from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from datetime import datetime
import hashlib
import json
import uuid

app = Flask(__name__)
app.secret_key = 'your-super-secret-key-change-in-production'

# Mock user database
users_db = {}
# Mock customers database
customers_db = {}
# Mock campaigns database
campaigns_db = {}

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

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
        
        if email in users_db and users_db[email]['password'] == password:
            session['user_id'] = users_db[email]['id']
            session['email'] = email
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        flash('Invalid credentials', 'error')
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        password = hash_password(request.form['password'])
        name = request.form['name']
        
        if email in users_db:
            flash('User already exists', 'error')
        else:
            user_id = str(uuid.uuid4())
            users_db[email] = {
                'id': user_id,
                'name': name,
                'password': password,
                'created_at': datetime.now().isoformat()
            }
            flash('Account created successfully!', 'success')
            return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully', 'success')
    return redirect(url_for('home'))

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/dashboard')
@login_required
def dashboard():
    total_customers = len(customers_db)
    total_campaigns = len(campaigns_db)
    active_campaigns = len([c for c in campaigns_db.values() if c['status'] == 'active'])
    
    return render_template('dashboard.html', 
                         total_customers=total_customers,
                         total_campaigns=total_campaigns,
                         active_campaigns=active_campaigns)

@app.route('/customers')
@login_required
def customers():
    return render_template('customers.html', customers=list(customers_db.values()))

@app.route('/customers/add', methods=['POST'])
@login_required
def add_customer():
    customer_id = str(uuid.uuid4())
    customers_db[customer_id] = {
        'id': customer_id,
        'name': request.form['name'],
        'email': request.form['email'],
        'preferences': request.form['preferences'],
        'purchase_history': [],
        'lifetime_value': float(request.form.get('lifetime_value', 0)),
        'created_at': datetime.now().isoformat()
    }
    flash('Customer added successfully!', 'success')
    return redirect(url_for('customers'))

@app.route('/campaign/new')
@login_required
def new_campaign():
    return render_template('campaign.html', customers=list(customers_db.values()))

@app.route('/campaign/create', methods=['POST'])
@login_required
def create_campaign():
    campaign_id = str(uuid.uuid4())
    customer_ids = request.form.getlist('customers')
    
    campaign_data = {
        'id': campaign_id,
        'name': request.form['name'],
        'type': request.form['type'],
        'target_customers': customer_ids,
        'status': 'active',
        'personalized_content': {},
        'created_at': datetime.now().isoformat(),
        'recommendations': {}
    }
    
    # Generate AI-driven personalized content
    for cust_id in customer_ids:
        if cust_id in customers_db:
            customer = customers_db[cust_id]
            recs = mock_aws_personalize(cust_id)
            content = generate_personalized_content(customer, request.form['type'])
            
            campaign_data['personalized_content'][cust_id] = content
            campaign_data['recommendations'][cust_id] = recs
    
    campaigns_db[campaign_id] = campaign_data
    flash('Campaign created with AI personalization!', 'success')
    return redirect(url_for('campaign_history'))

@app.route('/campaign/history')
@login_required
def campaign_history():
    return render_template('campaign_history.html', campaigns=list(campaigns_db.values()))

@app.route('/api/recommendations/<customer_id>')
@login_required
def get_recommendations(customer_id):
    if customer_id in customers_db:
        recs = mock_aws_personalize(customer_id)
        return jsonify(recs)
    return jsonify({'error': 'Customer not found'}), 404

@app.route('/campaign/<campaign_id>/preview')
@login_required
def campaign_preview(campaign_id):
    campaign = campaigns_db.get(campaign_id)
    if not campaign:
        flash('Campaign not found', 'error')
        return redirect(url_for('campaign_history'))
    
    return render_template('campaign.html', 
                         campaign=campaign,
                         customers=list(customers_db.values()))

if __name__ == '__main__':
    app.run(debug=True)
