import pandas as pd
import random

# Configuration
num_students = 50
start_did = 2024800001

# Data Pools
first_names = ["Arjun", "Aditi", "Rohan", "Sana", "Vikram", "Neha", "Aarav", "Ishani", "Kabir", "Ananya", 
               "Pranav", "Riya", "Aaryan", "Meera", "Siddharth", "Tanvi", "Ishaan", "Pooja", "Yash", "Zoya"]
last_names = ["Sharma", "Verma", "Patel", "Mehta", "Iyer", "Kulkarni", "Deshmukh", "Joshi", "Malhotra", "Reddy"]
universities = ["Sardar Patel Institute of Technology", "IIT Bombay", "BITS Pilani", "VJTI Mumbai"]
degrees = ["B.Tech", "B.E."]
branches = ["Computer Science and Engineering", "Information Technology", "Computer Engineering"]

data = []

for i in range(num_students):
    f_name = random.choice(first_names)
    l_name = random.choice(last_names)
    full_name = f"{f_name} {l_name}"
    
    student_did = start_did + i
    email = f"{f_name.lower()}.{l_name.lower()}{random.randint(10, 99)}@example.edu"
    uni = random.choice(universities)
    deg = random.choice(degrees)
    branch = random.choice(branches)
    
    # Generate a realistic CGPA between 7.5 and 9.8
    cgpa = round(random.uniform(7.5, 9.8), 2)
    
    # Year based on the DID prefix (2024)
    year = "2nd Year"
    
    data.append([full_name, student_did, email, uni, deg, branch, cgpa, year])

# Create DataFrame
df = pd.DataFrame(data, columns=["Student Name", "Student DID", "Student Email", "University Name", "Degree", "Branch", "CGPA", "Year"])
# Save to CSV
df.to_csv("student_credentials_dataset.csv", index=False)