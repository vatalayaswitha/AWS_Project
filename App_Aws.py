# App_Aws.py - AWS Global Deployment Flask App with DynamoDB
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from datetime import datetime
import hashlib
import json
import uuid
import boto3
from boto3.dynamodb.conditions import Key, Attr
import os
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-super-secret-key-change-in-production')

# AWS Configuration - Set these as Environment Variables
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
DYNAMODB_TABLES = {
    'Users': os.environ.get('USERS_TABLE', 'Users'),
    'Customers': os.environ.get('CUSTOMERS_TABLE', 'Customers'), 
    'Campaigns': os.environ.get('CAMPAIGNS_TABLE', 'Campaigns')
}

# Initialize DynamoDB Resource
dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
users_table = dynamodb.Table(DYNAMODB_TABLES['Users'])
customers_table = dynamodb.Table(DYNAMODB_TABLES['Customers'])
campaigns_table = dynamodb.Table(DYNAMODB_TABLES['Campaigns'])

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def mock_aws_personalize(customer_id):
    """Mock AWS Personalize recommendation"""
    recommendations = {
        'products': ['Premium Plan', 'Exclusive Offer', 'VIP Membership'],
        'content': 'Exclusive personalized offer just for you!',
        'urgency': 'Limited time - 24 hours left!'
    }
    return recommendations

def generate_personalized_content(customer_data, campaign_type):
    """Mock AWS Bedrock content generation"""
    templates = {
        'email': f"Hi {customer_data['name']}, {customer_data['preferences']} lovers unite! Get 30% OFF our premium collection.",
        'sms': f"{customer_data['name']}! Flash sale: 50% OFF your favorites. Tap now!",
        'push': f"🚀 {customer_data['name']}, your VIP deal awaits!"
    }
    return templates.get(campaign_type, "Personalized campaign content")

# ===== USER AUTHENTICATION ROUTES =====

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/index')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = hash_password(request.form['password'])
        
        try:
            response = users_table.query(
                KeyConditionExpression=Key('UserID').eq(email)
            )
            user = response['Items'][0] if response['Items'] else None
            
            if user and user['password'] == password:
                session['user_id'] = user['UserID']
                session['email'] = email
                flash('Login successful!', 'success')
                return redirect(url_for('dashboard'))
            flash('Invalid credentials', 'error')
        except Exception as e:
            flash('Login error occurred', 'error')
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        password = hash_password(request.form['password'])
        name = request.form['name']
        
        try:
            # Check if user exists
            response = users_table.query(
                KeyConditionExpression=Key('UserID').eq(email)
            )
            if response['Items']:
                flash('User already exists', 'error')
            else:
                user_id = email  # Use email as UserID
                users_table.put_item(Item={
                    'UserID': user_id,
                    'name': name,
                    'password': password,
                    'created_at': datetime.now().isoformat()
                })
                flash('Account created successfully!', 'success')
                return redirect(url_for('login'))
        except Exception as e:
            flash('Signup error occurred', 'error')
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully', 'success')
    return redirect(url_for('home'))

# ===== DASHBOARD & CUSTOMERS =====

@app.route('/dashboard')
@login_required
def dashboard():
    try:
        # Count customers
        customers_response = customers_table.scan()
        total_customers = len(customers_response['Items'])
        
        # Count campaigns
        campaigns_response = campaigns_table.scan()
        total_campaigns = len(campaigns_response['Items'])
        active_campaigns = len([c for c in campaigns_response['Items'] if c['status'] == 'active'])
        
        return render_template('dashboard.html', 
                             total_customers=total_customers,
                             total_campaigns=total_campaigns,
                             active_campaigns=active_campaigns)
    except Exception as e:
        flash('Dashboard load error', 'error')
        return render_template('dashboard.html', total_customers=0, total_campaigns=0, active_campaigns=0)

@app.route('/customers')
@login_required
def customers():
    try:
        response = customers_table.scan()
        customers_list = response['Items']
        return render_template('customers.html', customers=customers_list)
    except Exception as e:
        flash('Error loading customers', 'error')
        return render_template('customers.html', customers=[])

@app.route('/customers/add', methods=['POST'])
@login_required
def add_customer():
    try:
        customer_id = str(uuid.uuid4())
        customers_table.put_item(Item={
            'CustomerID': customer_id,
            'name': request.form['name'],
            'email': request.form['email'],
            'preferences': request.form['preferences'],
            'purchase_history': [],
            'lifetime_value': float(request.form.get('lifetime_value', 0)),
            'created_at': datetime.now().isoformat()
        })
        flash('Customer added successfully!', 'success')
    except Exception as e:
        flash('Error adding customer', 'error')
    return redirect(url_for('customers'))

# ===== CAMPAIGNS =====

@app.route('/campaign/new')
@login_required
def new_campaign():
    try:
        response = customers_table.scan()
        customers = response['Items']
        return render_template('campaign.html', customers=customers)
    except:
        return render_template('campaign.html', customers=[])

@app.route('/campaign/create', methods=['POST'])
@login_required
def create_campaign():
    try:
        campaign_id = str(uuid.uuid4())
        customer_ids = request.form.getlist('customers')
        
        campaign_data = {
            'CampaignID': campaign_id,
            'name': request.form['name'],
            'type': request.form['type'],
            'target_customers': customer_ids,
            'status': 'active',
            'personalized_content': {},
            'recommendations': {},
            'created_at': datetime.now().isoformat()
        }
        
        # Generate AI-driven personalized content
        for cust_id in customer_ids:
            try:
                customer_response = customers_table.get_item(Key={'CustomerID': cust_id})
                if 'Item' in customer_response:
                    customer = customer_response['Item']
                    recs = mock_aws_personalize(cust_id)
                    content = generate_personalized_content(customer, request.form['type'])
                    
                    campaign_data['personalized_content'][cust_id] = content
                    campaign_data['recommendations'][cust_id] = recs
            except:
                continue
        
        campaigns_table.put_item(Item=campaign_data)
        flash('Campaign created with AI personalization!', 'success')
    except Exception as e:
        flash('Error creating campaign', 'error')
    return redirect(url_for('campaign_history'))

@app.route('/campaign/history')
@login_required
def campaign_history():
    try:
        response = campaigns_table.scan()
        campaigns = response['Items']
        return render_template('campaign_history.html', campaigns=campaigns)
    except:
        return render_template('campaign_history.html', campaigns=[])

@app.route('/api/recommendations/<customer_id>')
@login_required
def get_recommendations(customer_id):
    try:
        if customers_table.get_item(Key={'CustomerID': customer_id}).get('Item'):
            recs = mock_aws_personalize(customer_id)
            return jsonify(recs)
    except:
        pass
    return jsonify({'error': 'Customer not found'}), 404

@app.route('/campaign/<campaign_id>/preview')
@login_required
def campaign_preview(campaign_id):
    try:
        response = campaigns_table.get_item(Key={'CampaignID': campaign_id})
        campaign = response['Item']
        customers_response = customers_table.scan()
        customers = customers_response['Items']
        return render_template('campaign.html', campaign=campaign, customers=customers)
    except:
        flash('Campaign not found', 'error')
        return redirect(url_for('campaign_history'))

if __name__ == '__main__':
    # Production deployment - Use gunicorn
    # gunicorn -w 4 -b 0.0.0.0:8000 App_Aws:app
    app.run(host='0.0.0.0', port=8000, debug=False)
