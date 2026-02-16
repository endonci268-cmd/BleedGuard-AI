ValueError: This app has encountered an error. The original error message is redacted to prevent data leaks. Full error details have been recorded in the logs (if you're on Streamlit Cloud, click on 'Manage app' in the lower right of your app).
Traceback:
File "/mount/src/bleedguard-ai/streamlit_app.py", line 95, in <module>
    prob = model.predict_proba(input_df)[0][1]
           ~~~~~~~~~~~~~~~~~~~^^^^^^^^^^
File "/home/adminuser/venv/lib/python3.13/site-packages/sklearn/linear_model/_logistic.py", line 1428, in predict_proba
    return super()._predict_proba_lr(X)
           ~~~~~~~~~~~~~~~~~~~~~~~~~^^^
File "/home/adminuser/venv/lib/python3.13/site-packages/sklearn/linear_model/_base.py", line 389, in _predict_proba_lr
    prob = self.decision_function(X)
File "/home/adminuser/venv/lib/python3.13/site-packages/sklearn/linear_model/_base.py", line 351, in decision_function
    X = validate_data(self, X, accept_sparse="csr", reset=False)
File "/home/adminuser/venv/lib/python3.13/site-packages/sklearn/utils/validation.py", line 2919, in validate_data
    _check_feature_names(_estimator, X, reset=reset)
    ~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^
File "/home/adminuser/venv/lib/python3.13/site-packages/sklearn/utils/validation.py", line 2777, in _check_feature_names
    raise ValueError(message)
