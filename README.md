# MT-analysis-toolkit
MT Post-editing analysis toolkit

### Usage

1. Put your Phrase credentials into a file called `memsource_credentials.yml` in the same format as `sample_memsource_credentials.yml`

2. Run the script with the name of the project

```
python Tool-notebook.py "Big translation project"
```

3. Analysis results for each job will be saved under `results`

### Notes

Development was done on IPython notebook `Tool-notebook.ipynb`. `Tool-notebook.py` is mere script export of the notebook.

### Automatic evaluation 

`bleu-evaluation` contains the notebooks and sample data for doing automatic evaluation on Hausa with [NLLB model](https://huggingface.co/docs/transformers/v4.28.1/en/model_doc/nllb). 