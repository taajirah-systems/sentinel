import stripe
import os

# This is a placeholder for your Stripe API key.
# In a real application, you would set this as an environment variable.
stripe.api_key = os.environ.get('STRIPE_API_KEY', 'sk_test_your_key_here')

# Placeholder for your pricing plan IDs from your Stripe dashboard
PRICE_IDS = {
    'developer': 'price_123developer',
    'business': 'price_123business',
}

def create_checkout_session(customer_email: str, plan: str):
    """Creates a Stripe checkout session for a given customer and plan."""
    if plan not in PRICE_IDS:
        raise ValueError(f'Invalid plan specified: {plan}')

    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[
                {
                    'price': PRICE_IDS[plan],
                    'quantity': 1,
                },
            ],
            mode='subscription',
            customer_email=customer_email,
            success_url='https://your-domain.com/success?session_id={CHECKOUT_SESSION_ID}',
            cancel_url='https://your-domain.com/cancel',
        )
        return checkout_session.url
    except Exception as e:
        # Handle potential exceptions from the Stripe API
        return str(e)

if __name__ == '__main__':
    # Example usage:
    # This would be triggered by a user selecting a plan on your landing page.
    customer_email = 'customer@example.com'
    plan = 'developer' # or 'business'
    
    checkout_url = create_checkout_session(customer_email, plan)
    
    print(f'To subscribe {customer_email} to the {plan} plan, send them to this URL:')
    print(checkout_url)
