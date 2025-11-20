import csv  # Import the built-in csv module

def read_file_to_dict(file_path):
    """
    Reads a semicolon-delimited CSV file (even multiline) 
    into a dictionary of columns.
    
    Output format: {'Header1': ['val1', 'val2'], 'Header2': ['valA', 'valB']}
    """
    data = {}
    try:
        # 'newline=""' is the standard recommendation when working with the csv module
        with open(file_path, 'r', encoding='utf-8-sig', newline='') as file:
            
            # Create a reader object that understands semicolons
            reader = csv.reader(file, delimiter=';')
            
            # Read the first row as the header
            headers = next(reader)
            
            # Read all remaining rows into a list
            # The reader handles multiline fields automatically
            all_rows = list(reader)
            
            # This is the "transpose" step, same as your original logic
            # zip(*all_rows) groups data by column
            # zip(headers, ...) pairs each header with its column data
            for header, column_values in zip(headers, zip(*all_rows)):
                data[header] = list(column_values)
                
    except FileNotFoundError:
        print(f"File not found: {file_path}")
    except StopIteration:
        # This happens if the file is completely empty
        print(f"File is empty: {file_path}")
    except Exception as e:
        print(f"Error reading file: {e}")
        
    return data