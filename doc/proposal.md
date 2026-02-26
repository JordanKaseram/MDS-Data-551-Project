# Designing a Profitable Summer Campaign: Acquiring New Customers Without Sacrificing Margin

---

## 1. Motivation and Purpose

**Our role:** Data analytics consulting team  
**Target audience:** Marketing managers and retail strategy leaders  

Retail organizations frequently launch seasonal campaigns to boost sales, but these campaigns often rely heavily on discounts, which can attract customers at the expense of profit margins. Our client plans to launch a Summer Campaign and wants to understand how to attract new customers, increase basket size, and remain profitable at the same time.

The goal of this project is to build an interactive data visualization application that supports campaign decision-making. Specifically, our dashboard will help retail stakeholders identify acquisition (“hero”) products, profitable attach products, and high-potential new customers. By combining descriptive analytics, market basket analysis, and predictive modeling, our app will allow users to design a data-driven campaign strategy rather than relying on intuition alone.

---

## 2. Description of the Data

We will use a transactional retail dataset containing approximately 50,000 orders. Each transaction includes information at the order, customer, product, and operational levels.

At a high level, the dataset contains:

- **Order information:** order ID, order date, ship mode  
- **Customer information:** customer ID, segment, region  
- **Product information:** product name, category, sub-category  
- **Financial metrics:** sales (revenue), profit, discount, quantity  

From the raw data, we will derive several new variables to support analysis and modeling:

- **Profit margin:** profit divided by sales  
- **First purchase flag:** identifies each customer’s first transaction  
- **New customer indicator:** customers with only one historical order or whose first order occurred within a defined recent window  
- **Conversion label:** whether a new customer places a second order within a fixed time period  
- **Basket-level features:** total basket value, number of items, average discount  
- **Model outputs:** predicted probability that a new customer will convert or become profitable  

These derived variables allow us to move beyond descriptive reporting toward customer acquisition analytics and predictive decision support.

---

## 3. Research Questions and Usage Scenarios

Our application is designed around a realistic consulting scenario.

### Persona

Alex is a retail marketing manager responsible for planning a Summer Campaign. Alex wants to grow the customer base while protecting profit margins. Historically, campaigns have increased revenue but led to margin erosion due to aggressive discounting. Alex needs evidence-based guidance on which products to promote, how to bundle items, and which customers to target.

---

### Core Research Questions

Our dashboard will help Alex explore the following questions:

1. **Are sales growth and profit growth aligned?**  
   Alex begins by reviewing overall revenue, profit, and margin trends to understand current business trend.

2. **Which categories generate revenue versus profit?**  
   Alex compares sales and profit by category to identify areas where high revenue masks low or negative margins.

3. **Which products attract new customers (hero products)?**  
   By examining first-time purchases, Alex identifies products that frequently appear in customers’ initial orders. These become potential acquisition drivers.

4. **Which products generate strong margins (profit drivers)?**  
   Alex analyzes profit margin by product and sub-category to find items suitable for cross-selling or bundling.

5. **What products are commonly purchased together?**  
   Using market basket analysis (Apriori), Alex explores associations between hero products and profitable attach products. These relationships inform bundle design.

6. **What do new customers typically buy in their first basket?**  
   Alex filters to first transactions only and examines basket size, discount usage, and product mix to understand entry-level behavior.

7. **Which new customers convert into repeat buyers?**  
   Alex reviews how first-basket characteristics relate to repeat purchases, discovering that some new customer profiles convert at much higher rates than others.

8. **Can we predict which new customers will become valuable?**  
   A classification model (logistic regression or random forest) uses first-order features—such as basket value, discount level, category mix, margin and demographic to estimate each new customer’s probability of conversion.

9. **At what discount level does profit collapse?**  
   Alex examines profit across discount buckets to establish pricing guardrails for the campaign.

---

### Usage Scenario

Alex logs into the dashboard and first views an executive overview showing sales, profit, and margin trends. Noticing that profit growth lags behind revenue, Alex navigates to the category comparison page and discovers that certain categories generate strong sales but consistently low margins.

Next, Alex explores the “New Customer Entry” section, which highlights hero products based on first purchases. Alex selects one hero product and views associated attach products derived from basket analysis. The dashboard reveals that customers who purchase this hero item frequently add a high-margin accessory to their basket.

Alex then moves to the “New Customer Intelligence” page, where customers are segmented based on their first-order behavior. A predictive model assigns conversion probabilities to new buyers. Alex filters to customers with high predicted conversion likelihood and observes that these customers tend to purchase moderate-sized baskets with limited discounts.

Finally, Alex reviews the campaign simulation page, which combines hero products, attach products, target customer segments, and discount thresholds. Based on these insights, Alex designs a Summer Campaign that promotes a high-acquisition hero product, bundles it with a profitable attach item, targets new customers with high predicted conversion probability, and caps discounts at a level that preserves margin.

---

