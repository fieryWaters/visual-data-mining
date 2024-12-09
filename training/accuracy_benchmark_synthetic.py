import torch
import gc
from contextlib import contextmanager
from datasets import load_dataset
import os
from PIL import Image, ImageDraw
import matplotlib.pyplot as plt
from transformers import MllamaForConditionalGeneration, MllamaProcessor
import math
import numpy as np

class ModelMemoryManager:
    @contextmanager
    def load_model(self, model_class, model_name, processor_class=None, peft_model_path=None, **kwargs):
        try:
            model = model_class.from_pretrained(model_name, **kwargs)
            if peft_model_path:
                from peft import PeftModel
                model = PeftModel.from_pretrained(model, peft_model_path)
            processor = processor_class.from_pretrained(model_name) if processor_class else None
            yield model, processor
        finally:
            del model
            if processor:
                del processor
            torch.cuda.empty_cache()
            gc.collect()

def calculate_distance(point1, point2):
    return math.sqrt((point1[0] - point2[0])**2 + (point1[1] - point2[1])**2)

def process_batch(model, processor, dataset, start_index, batch_size, show_images=False):
    # Initialize error tracking
    total_error = 0
    errors = []  # List to store all errors for std calculation
    successful_predictions = 0
    failed_predictions = []

    for i in range(batch_size):
        index = start_index + i
        image = dataset[index]['images']
        prompt = dataset[index]['texts'][0]['user']
        
        # Process image directly without temp file
        img_for_model = image.convert("RGB")
        conversation = [
            {
                "role": "user",
                "content": [{"type": "image"}, {"type": "text", "text": prompt}],
            }
        ]
        prompt_text = processor.apply_chat_template(
            conversation, add_generation_prompt=True, tokenize=False
        )

        inputs = processor(img_for_model, prompt_text, return_tensors="pt").to(model.device)
        output = model.generate(
            **inputs,
            temperature=0.5,
            top_p=0.8,
            max_new_tokens=512,
        )

        pred = processor.decode(output[0])[len(prompt_text):]

        # Process coordinates after model inference
        true_coord = [float(x) for x in dataset[index]['texts'][0]['assistant'].strip('[]').split(',')]
        
        try:
            pred_numbers = pred.split('|>')[1].split('<|')[0].strip()
            pred_coord = [float(x) for x in pred_numbers.strip('[]').split(',')]
            
            # Calculate distance between predicted and true coordinates
            distance = calculate_distance(true_coord, pred_coord)
            
            total_error += distance
            errors.append(distance)
            successful_predictions += 1
            
            if show_images:
                draw = ImageDraw.Draw(image)
                # Draw circles at the true and predicted points
                radius = 5  # Size of the point markers
                draw.ellipse([true_coord[0]-radius, true_coord[1]-radius, 
                            true_coord[0]+radius, true_coord[1]+radius], 
                           fill='green')  # True coordinate
                draw.ellipse([pred_coord[0]-radius, pred_coord[1]-radius, 
                            pred_coord[0]+radius, pred_coord[1]+radius], 
                           fill='red')   # Predicted coordinate
                plt.figure(figsize=(12,8))
                plt.imshow(image)
                plt.axis('off')
                plt.show()
                plt.close()
                
                # Print metrics after each image
                print(f"\nMetrics for image {index}:")
                print(f"Coordinate error: {distance:.2f} pixels")
            
        except Exception as e:
            print(f"Error parsing prediction at index {index}: {e}")
            print(f"Raw prediction: {pred}")
            failed_predictions.append(index)
    
    # Print final statistics
    if successful_predictions > 0:
        avg_error = total_error / successful_predictions
        std_error = np.std(errors)
        
        print(f"\nFinal Results:")
        print(f"Coordinate Prediction:")
        print(f"  Average distance error: {avg_error:.2f} pixels")
        print(f"  Standard deviation: {std_error:.2f} pixels")
        print(f"  Successful predictions: {successful_predictions}")
    print(f"Failed predictions at indices: {failed_predictions}")
    print(f"Number of failures: {len(failed_predictions)}")

# First do the dataset loading and splitting
split_ratio = 0.9
dataset_dict = load_dataset("jwaters8978/synthetic_dataset", name="default")
dataset = dataset_dict['train']
#dataset = dataset.select(range(100))

# First split into train and temp
temp_dataset = dataset.train_test_split(test_size=0.2, shuffle=True, seed=42)
train_data = temp_dataset['train']  # 80%

# Second split: Split the temp into validation and test
val_test_dataset = temp_dataset['test'].train_test_split(test_size=0.5, shuffle=True, seed=42)
val_data = val_test_dataset['train']    # 10%
test_data = val_test_dataset['test']    # 10%

print("ANALYZING IMAGE ACCURACY")

# Main execution
manager = ModelMemoryManager()
with manager.load_model(
    MllamaForConditionalGeneration,
    "meta-llama/Llama-3.2-11B-Vision-Instruct",
    MllamaProcessor,
    peft_model_path="finetuned_model/fine-tuned/peft_weights/",
    torch_dtype=torch.bfloat16,
    device_map="auto",
    use_safetensors=True
) as (model, processor):
    process_batch(model, processor, test_data, start_index=0, batch_size=180, show_images=False)