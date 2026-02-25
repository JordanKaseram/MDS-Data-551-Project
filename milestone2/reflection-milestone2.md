# Reflection: Milestone 2


---

## 1. Implementation Progress
We have successfully established the **core framework** of the dashboard. The current version provides a high-level descriptive analysis of the business through three primary visualizations:
* **Total Sales Trend (2011-2014):** A longitudinal view of revenue growth over a four-year period.
* **Category-wise Sales Distribution:** A breakdown of sales performance across different business sectors (Technology, Furniture, and Office Supplies).
* **Top 10 Products by Profitability:** A focused bar chart identifying the individual items contributing most to the bottom line.

The underlying **data pipeline** and **layout structure** are fully functional, providing a stable base for the integration of future interactive features.

---

## 2. Deviations from Original Plan
Our initial objective was to develop a sophisticated **"Hero Product Discovery"** dashboard, as conceptualized in our early mockups. However, as we progressed into the implementation phase, we made a strategic pivot for the following reasons:

* **Data Constraints:** Upon a deep dive into the dataframe, we discovered the temporal data only spans **four years**. This time horizon is insufficient to support the long-term lifecycle modeling and predictive "Hero Product" analysis we originally envisioned. 
* **Prioritizing Accuracy:** To maintain data integrity, we pivoted to a descriptive analysis approach. We chose to provide accurate, high-fidelity insights from the available data rather than building complex simulations that the current dataset could not reliably support.

---

## 3. Limitations
* **Aesthetic Polish:** The visual encoding, color schemes, and overall design hierarchy are not yet refined to a professional standard.
* **Limited Interactivity:** Interactivity is currently in its early stages. At present, only the "Top 10 Products" chart supports user engagement, while other components remain static.
* **Logical Correlation:** The data groups (Sales, Category, and Profit) function as independent modules. They currently lack a **strong relational bridge**, which limits the user's ability to draw cross-functional insights from the dashboard as a whole.

---

## 4. Future Improvements
To address the limitations identified in this milestone, our group will focus on the following enhancements for the final delivery:
1.  **Refine UI/UX:** Optimize the dashboard's aesthetics by implementing a cohesive color palette and improving layout consistency to achieve a more professional and intuitive user experience.
2.  **Enhance Interactivity:** Develop full **cross-filtering** and dynamic **callbacks** across all charts, allowing users to explore the data from multiple dimensions simultaneously.
3.  **Strengthen Data Narrative:** Investigate more complex statistical relations to link separate data groups, creating a more unified and compelling business story that connects sales trends with product-level profitability.


```python

```
