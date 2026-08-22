/**
 * Stripe Payment Element Handler
 */
async function processStripePayment(amount, description) {
  console.log(`[Stripe] Initializing checkout for $${amount} (${description})`);
  return await APIClient.post("/api/payments/intent/create/", {
    amount: amount,
    description: description
  });
}
