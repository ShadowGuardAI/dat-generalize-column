import argparse
import pandas as pd
import logging
import re
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def setup_argparse():
    """
    Sets up the argument parser for the command-line interface.
    """
    parser = argparse.ArgumentParser(description="Generalizes a column in a CSV file by replacing values with more general categories.")
    parser.add_argument("input_file", help="Path to the input CSV file.")
    parser.add_argument("output_file", help="Path to the output CSV file.")
    parser.add_argument("column_name", help="Name of the column to generalize.")
    parser.add_argument("--lookup_file", help="Path to a CSV file containing the lookup table (value,generalized_value).", required=False)
    parser.add_argument("--regex", help="Regular expression pattern and replacement string (pattern::replacement).", required=False)

    return parser

def generalize_column(df, column_name, lookup_file=None, regex=None):
    """
    Generalizes the specified column based on either a lookup table or a regular expression.

    Args:
        df (pd.DataFrame): The Pandas DataFrame to process.
        column_name (str): The name of the column to generalize.
        lookup_file (str, optional): Path to a CSV file for lookup generalization. Defaults to None.
        regex (str, optional): Regular expression and replacement string (pattern::replacement). Defaults to None.

    Returns:
        pd.DataFrame: The modified DataFrame with the generalized column.

    Raises:
        ValueError: If neither lookup_file nor regex is provided, or if both are provided.
        FileNotFoundError: If the lookup_file does not exist.
        Exception: For other unexpected errors during processing.
    """
    try:
        if lookup_file and regex:
            raise ValueError("Only one of --lookup_file or --regex can be specified.")
        elif not lookup_file and not regex:
            raise ValueError("Either --lookup_file or --regex must be specified.")

        if lookup_file:
            try:
                lookup_df = pd.read_csv(lookup_file)
                if lookup_df.shape[1] != 2:
                    raise ValueError(f"Lookup file {lookup_file} must have exactly two columns (value, generalized_value).  It has {lookup_df.shape[1]} columns.")
                lookup_dict = dict(zip(lookup_df.iloc[:, 0].astype(str), lookup_df.iloc[:, 1].astype(str))) # Ensure keys are strings.
                df[column_name] = df[column_name].astype(str).map(lookup_dict).fillna(df[column_name]) #Ensures nulls are handled by retaining original value
            except FileNotFoundError:
                logging.error(f"Lookup file not found: {lookup_file}")
                raise
            except Exception as e:
                 logging.error(f"Error processing lookup file {lookup_file}: {e}")
                 raise

        elif regex:
            try:
                pattern, replacement = regex.split("::", 1)
                df[column_name] = df[column_name].astype(str).replace(pattern, replacement, regex=True)
            except ValueError:
                logging.error("Invalid regex format.  Use 'pattern::replacement'.")
                raise
            except Exception as e:
                logging.error(f"Error applying regex: {e}")
                raise

        return df

    except ValueError as e:
        logging.error(e)
        raise
    except FileNotFoundError as e:
        raise e # Re-raise to allow main() to handle it.
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        raise


def main():
    """
    Main function to execute the data generalization process.
    """
    parser = setup_argparse()
    args = parser.parse_args()

    try:
        # Input validation: File extension check
        if not args.input_file.lower().endswith('.csv'):
            raise ValueError("Input file must be a CSV file.")

        if not args.output_file.lower().endswith('.csv'):
             raise ValueError("Output file must be a CSV file.")

        df = pd.read_csv(args.input_file)

        # Input validation: Column name check
        if args.column_name not in df.columns:
            raise ValueError(f"Column '{args.column_name}' not found in the input file.")


        generalized_df = generalize_column(df.copy(), args.column_name, args.lookup_file, args.regex)

        # Securely write to the output file (avoiding potential path traversal vulnerabilities)
        generalized_df.to_csv(args.output_file, index=False)
        logging.info(f"Generalized data saved to {args.output_file}")

    except FileNotFoundError:
        logging.error(f"Input file not found: {args.input_file}")
        sys.exit(1)  # Exit with an error code
    except ValueError as e:
        logging.error(e)
        sys.exit(1) # Exit with an error code.
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        sys.exit(1)  # Exit with an error code



if __name__ == "__main__":
    main()


"""
Usage Examples:

1. Generalize ages in 'age' column using a lookup table:
   python main.py input.csv output.csv age --lookup_file age_lookup.csv
   Where age_lookup.csv contains:
   age,age_group
   18,18-25
   19,18-25
   26,26-35
   27,26-35
   ...

2. Generalize phone numbers using regex (replace all digits with X):
   python main.py input.csv output.csv phone_number --regex "\d::X"

3. Demonstrating Error Handling (missing file):
   python main.py missing.csv output.csv age --lookup_file age_lookup.csv

4. Demonstrating Error Handling (invalid regex):
    python main.py input.csv output.csv phone_number --regex "\d" # missing :: replacement

5. Demonstrating Error Handling (column doesn't exist):
   python main.py input.csv output.csv non_existent_column --lookup_file age_lookup.csv
"""