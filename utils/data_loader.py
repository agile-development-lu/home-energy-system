import pandas as pd
import json

def json_to_dataframe(json_input):
    """
    Convert a JSON string or dictionary to a pandas DataFrame.
    
    Parameters:
        json_input (str or dict): JSON data as a string or a dictionary.
        
    Returns:
        pd.DataFrame: A DataFrame constructed from the JSON data.
    """
    # If the input is a string, parse it into a Python object.
    if isinstance(json_input, str):
        data = json.loads(json_input)
    else:
        data = json_input
    # Create a DataFrame from the data.
    df = pd.DataFrame(data)
    return df

def dataframe_to_json(df, orient='records', indent=4):
    """
    Convert a pandas DataFrame to a JSON string.
    
    Parameters:
        df (pd.DataFrame): The DataFrame to convert.
        orient (str): String specifying the format of the JSON output.
                      Common values include 'records', 'split', 'index', etc.
        indent (int): Number of spaces for indentation in the output JSON string.
        
    Returns:
        str: A JSON formatted string.
    """
    # Use the DataFrame's built-in to_json method.
    json_str = df.to_json(orient=orient, indent=indent)
    return json_str

# Example usage:
# if __name__ == "__main__":
#     df = pd.read_csv("../static/weather_forecast_7days.csv")
#     print("DataFrame:")
#     print(df)
#     json_output = dataframe_to_json(df)
#     print("Json:", json_output)
#     df = json_to_dataframe(json_output)
#     print("DataFrame:")
#     print(df)
