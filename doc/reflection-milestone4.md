# Reflection: Milestone 4

## Overview

For the final milestone, our main goal was to turn the dashboard from a working analytical prototype into a more production-ready application. The biggest improvement was not just adding more charts, but improving the overall usability, clarity, and decision flow of the app. In earlier milestones, our dashboard included multiple interesting analyses, but some sections felt disconnected or too technical for a general business user. In this final version, we focused on making the dashboard easier to understand, easier to navigate, and better aligned with the core business question: how to improve profit through better product and pricing decisions.

## What We Implemented

- Reorganized the dashboard around a clearer analytical flow, starting with a **subcategory opportunity** view and then drilling down into a **product breakdown** view.
- Built a stronger link between the main visuals so users can move from high-level subcategory insights to specific product-level decisions more naturally.
- Added a **discount guardrail** chart to help users evaluate how discount levels relate to profit outcomes across subcategories.
- Expanded the filtering options beyond a simple year input by adding **year range**, **season**, and **customer segment** controls.
- Improved the overall layout for a more production-ready, full-screen experience with less unnecessary scrolling.
- Refined the presentation of the app by improving organization, readability, and visual hierarchy.
- Added a browser tab title, `Profit Optimization Strategy for Retail Campaigns`, to make the application feel more complete and polished.

## Feedback and Design Decisions

Peer feedback was especially valuable in shaping the final version. Reviewers asked for more filters, better readability in the lower charts, clearer use of color, and a more intuitive interface overall. We addressed these points by refining chart sizing, improving visual distinction between metrics, and reorganizing the page so the most important content appears first. Another recurring theme in the feedback was clarity for non-technical users. This directly influenced one of our biggest final design decisions: we removed the basket market analysis / bundle opportunities table from the final dashboard. Although that component was analytically interesting, it was difficult to interpret quickly and added complexity without enough user-facing value. We chose to prioritize interpretability and usability over keeping every advanced feature.

## Final Reflection

The most important lesson from this milestone was that a strong dashboard is not only about analytical depth, but also about communication. A feature can be technically correct and still not belong in the final product if it confuses users or interrupts the story. Our final dashboard is more focused, more coherent, and more practical because we made deliberate tradeoffs based on feedback. If we continued developing the app, the next steps would be improving accessibility, documenting feedback responses more explicitly, and further tuning responsive behavior across screen sizes.
