import argparse
import yaml
from .predictor import run_prediction

def main():
    parser = argparse.ArgumentParser(description="PostgreSQL storage analyzer")
    parser.add_argument("config", help="Path to YAML config file", default="config.yaml", nargs='?')
    args = parser.parse_args()

    try:
        with open(args.config, "r") as f:
            config = yaml.safe_load(f)['load_prediction_config']
    except FileNotFoundError:
        print(f"Error: Config file '{args.config}' not found!")
        exit(1)
    except yaml.YAMLError as e:
        print(f"YAML parsing error: {e}")
        exit(1)

    print(run_prediction(config))
