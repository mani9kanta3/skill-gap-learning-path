"""
Word lists for names. All written for this project, none copied from a
dataset, so there is nothing to license and no real person in the data.

Skill names are "<topic> <aspect>". Every category has 10 topics and
every topic pairs with 5 aspects, which gives exactly 50 unique names per
category: the full scale. Smaller scales take a seeded sample of them.
"""

ASPECTS = ("Fundamentals", "Design", "Automation", "Troubleshooting", "Strategy")

TOPICS = {
    "Software Engineering": (
        "Python", "Java", "API", "Microservice", "Testing",
        "Code Review", "Frontend", "Version Control", "Refactoring", "Secure Coding",
    ),
    "Data & AI": (
        "SQL", "Data Modelling", "Statistics", "Machine Learning", "Data Visualisation",
        "Data Quality", "ETL", "Forecasting", "Experimentation", "Prompt Engineering",
    ),
    "Infrastructure & Cloud": (
        "Cloud Networking", "Linux", "Containers", "Kubernetes", "Infrastructure as Code",
        "Monitoring", "Identity Management", "Backup", "Incident Response", "Cost Management",
    ),
    "Sales": (
        "Prospecting", "Negotiation", "Account Planning", "Pipeline", "Solution Selling",
        "Pricing", "Contract", "Territory", "CRM", "Renewal",
    ),
    "Marketing": (
        "Brand", "Content", "Campaign", "SEO", "Social Media",
        "Market Research", "Email Marketing", "Product Marketing", "Event", "Marketing Analytics",
    ),
    "Finance": (
        "Budgeting", "Financial Reporting", "Cash Flow", "Audit", "Tax",
        "Cost Accounting", "Financial Modelling", "Procurement", "Risk Control", "Payroll",
    ),
    "People & HR": (
        "Recruiting", "Onboarding", "Performance Review", "Compensation", "Employee Relations",
        "Learning Design", "Workforce Planning", "HR Policy", "Wellbeing", "HR Analytics",
    ),
    "Operations & Supply Chain": (
        "Inventory", "Logistics", "Process Improvement", "Quality Control", "Supplier",
        "Demand Planning", "Warehouse", "Lean", "Health and Safety", "Capacity Planning",
    ),
    "Leadership & Communication": (
        "Presentation", "Coaching", "Feedback", "Stakeholder", "Conflict Resolution",
        "Decision Making", "Team Leadership", "Business Writing", "Facilitation", "Change Management",
    ),
    "Digital Productivity": (
        "Spreadsheet", "Collaboration Tools", "Time Management", "Document Management", "Workflow",
        "Dashboard", "Data Privacy", "Knowledge Base", "Remote Working", "Accessibility",
    ),
}

# Role title per career level: "<department name> <title>".
LEVEL_TITLES = {1: "Associate", 2: "Specialist", 3: "Senior Specialist", 4: "Lead", 5: "Principal"}

# Course title suffixes. The first and second course of a skill use
# different suffixes, so titles are unique even when both share a level.
FIRST_COURSE_SUFFIX = {"FOUNDATION": "Foundations", "INTERMEDIATE": "Workshop"}
SECOND_COURSE_SUFFIX = {"INTERMEDIATE": "Applied Lab", "ADVANCED": "Masterclass"}

FIRST_NAMES = (
    "Aarav", "Aditi", "Akash", "Ananya", "Arjun", "Bhavna", "Chen", "Deepa", "Divya", "Elena",
    "Farah", "Gaurav", "Hana", "Ishaan", "Jaya", "Karan", "Kavya", "Leo", "Maya", "Meera",
    "Nikhil", "Nisha", "Omar", "Priya", "Rahul", "Riya", "Rohan", "Sana", "Sara", "Siddharth",
    "Sneha", "Tara", "Tomas", "Uma", "Varun", "Vikram", "Wei", "Yash", "Zara", "Zoya",
)

LAST_NAMES = (
    "Agarwal", "Bose", "Chopra", "Das", "Fernandes", "Ghosh", "Gupta", "Iyer", "Jain", "Joshi",
    "Kapoor", "Khan", "Kumar", "Mehta", "Menon", "Mishra", "Nair", "Patel", "Pillai", "Rao",
    "Reddy", "Roy", "Saxena", "Sen", "Shah", "Sharma", "Singh", "Srinivasan", "Thomas", "Verma",
)
