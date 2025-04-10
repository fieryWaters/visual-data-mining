# Building the Data Collector GUI

## Windows
1) open cmd.exe
2) Make sure python 3.11 installed
3) run following commands:
```
py -3.11 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python build_app.py
```
The executable will be created as `data_collection_GUI.exe`

## Linux/Mac
```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python build_app.py
```
The executable will be created as `data_collection_GUI`