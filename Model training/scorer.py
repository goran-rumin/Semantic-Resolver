from sklearn.metrics import f1_score

def f1_scorer(estimator, X, y):
    y_predicted = estimator.predict(X)
    return f1_score(y, y_predicted, average="macro")