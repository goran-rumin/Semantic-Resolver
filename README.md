# Semantic Resolver

This project contains training data and procedure of NLP model for relation extraction, web service that uses model
for news processing and Chrome extension that shows relations to users.

## Training
For traning procedure see "Model training" Jupyter notebook in "Model training" folder. Training data files 
in same folder contain preprocessed and annotated training sentences from Reuters and Brown datasets.

## Semantic processing
See semantic.py in "Web service" folder. Evaluation results with used texts are in "Web service/evaluation" folder.

## Service
Entrypoint is relation_extractor_web.py in "Web service" folder. Service requires running MySQL instance. 
Check database_mysql.py for details.

## Chrome extension
Source is in "Chrome extension" folder. It could be easily installed by enabling "Developer mode" at chrome://extensions/
and selecting "Load unpacked".