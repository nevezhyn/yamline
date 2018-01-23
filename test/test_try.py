from yamline import get_pipeline

if __name__ == '__main__':
    pipeline = get_pipeline('specifications/test1.yaml')
    pipeline.execute()
