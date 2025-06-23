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

def convert_to_pixels(bbox, image_size):
   x_res, y_res = image_size
   return [
       bbox[0] * x_res / 100,
       bbox[1] * y_res / 100,
       bbox[2] * x_res / 100,
       bbox[3] * y_res / 100
   ]

def calculate_distance(point1, point2):
   return math.sqrt((point1[0] - point2[0])**2 + (point1[1] - point2[1])**2)

def process_batch(model, processor, dataset, start_index, batch_size, show_images=False):
   # Initialize error tracking for single click points
   total_error = 0
   errors = []  # List to store all errors for std calculation
   successful_predictions = 0
   failed_predictions = []
   
   for i in range(batch_size):
       index = start_index + i
       if index >= len(dataset):
           break
           
       image = dataset[index]['images'][0]  # Get the first (and only) image from the list
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
       
       # Process click coordinates from assistant response
       true_coords = [float(x) for x in dataset[index]['texts'][0]['assistant'].strip('[]').split(',')]
       true_x, true_y = true_coords[0], true_coords[1]
       
       try:
           pred_numbers = pred.split('|>')[1].split('<|')[0].strip()
           pred_coords = [float(x) for x in pred_numbers.strip('[]').split(',')]
           pred_x, pred_y = pred_coords[0], pred_coords[1]
           
           # Calculate distance for the click point
           click_distance = calculate_distance([true_x, true_y], [pred_x, pred_y])
           
           total_error += click_distance
           errors.append(click_distance)
           successful_predictions += 1
           
           if show_images:
               draw = ImageDraw.Draw(image)
               # Draw true click point (green circle)
               radius = 10
               draw.ellipse([true_x-radius, true_y-radius, true_x+radius, true_y+radius], 
                          outline='green', width=3)
               # Draw predicted click point (red circle)
               draw.ellipse([pred_x-radius, pred_y-radius, pred_x+radius, pred_y+radius], 
                          outline='red', width=3)
               # Draw line between them
               draw.line([(true_x, true_y), (pred_x, pred_y)], fill='yellow', width=2)
               
               plt.figure(figsize=(12,8))
               plt.imshow(image)
               plt.axis('off')
               plt.title(f"Click Point Error: {click_distance:.2f} pixels")
               plt.show()
               plt.close()
               
               # Print metrics after each image
               print(f"\nMetrics for image {index}:")
               print(f"True click: ({true_x:.1f}, {true_y:.1f})")
               print(f"Predicted click: ({pred_x:.1f}, {pred_y:.1f})")
               print(f"Distance error: {click_distance:.2f} pixels")
           
       except Exception as e:
           print(f"Error parsing prediction at index {index}: {e}")
           print(f"Raw prediction: {pred}")
           failed_predictions.append(index)
   
   # Print final statistics
   if successful_predictions > 0:
       avg_error = total_error / successful_predictions
       std_error = np.std(errors)
       
       print(f"\nFinal Results:")
       print(f"Click Point Accuracy:")
       print(f"  Average distance error: {avg_error:.2f} pixels")
       print(f"  Standard deviation: {std_error:.2f} pixels")
       print(f"  Min error: {min(errors):.2f} pixels")
       print(f"  Max error: {max(errors):.2f} pixels")
       print(f"  Median error: {np.median(errors):.2f} pixels")
       print(f"\nSuccess Rate:")
       print(f"  Successful predictions: {successful_predictions}")
       print(f"  Total attempts: {min(batch_size, len(dataset) - start_index)}")
       print(f"  Success rate: {successful_predictions / min(batch_size, len(dataset) - start_index) * 100:.1f}%")
   print(f"\nFailed predictions at indices: {failed_predictions}")
   print(f"Number of failures: {len(failed_predictions)}")

# # First do the dataset loading and splitting
# split_ratio = 0.9
# dataset_dict = load_dataset("jwaters8978/web_scraper_dataset", name="default")
# dataset = dataset_dict['train']
# #dataset = dataset.select(range(100))

# # First split into train and temp
# temp_dataset = dataset.train_test_split(test_size=0.2, shuffle=True, seed=42)
# train_data = temp_dataset['train']  # 80%

# # Second split: Split the temp into validation and test
# val_test_dataset = temp_dataset['test'].train_test_split(test_size=0.5, shuffle=True, seed=42)
# val_data = val_test_dataset['train']    # 10%
# test_data = val_test_dataset['test']    # 10%

from tokenize_dataset import get_custom_dataset

# Load test split (20% of data)
test_dataset = get_custom_dataset(None, None, "test", 0.8)

print("ANALYZING CLICK POINT ACCURACY")
print(f"Test dataset size: {len(test_dataset)}")

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

   process_batch(model, processor, test_dataset, start_index=0, batch_size = 20, show_images=True)