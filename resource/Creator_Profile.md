:---
title: "Understanding the Creator Profile" doc_id: "concept-005" type: "Concept" feature_area: ["Creator Profiles"] prerequisites: [] unlocks: ["task-012"] keywords: ["creator profile", "creator stats", "audience demographics", "vetting", "influencer analytics"] user_level: "Beginner" last_updated: "2025-09-26"
What is this?
The Creator Profile is a centralized dashboard containing all the data and insights we have about a specific creator. It consolidates everything from performance metrics and audience demographics to their latest content and contact information.

Why is it useful?
This profile is your single source of truth for vetting. It saves you the immense effort of manually piecing together information from various social platforms. By providing a 360-degree view of a creator's performance, audience, and content, it empowers you to make fast, data-driven decisions about whether they are the right fit for your brand. This directly supports your goal of building high-performing, brand-safe campaign rosters.

:---
title: "Understanding the Creator Safety Score" doc_id: "concept-006" type: "Concept" feature_area: ["Creator Profiles"] prerequisites: [] unlocks: ["faq-008", "faq-009"] keywords: ["safety score", "brand safety", "vetting", "risk management", "unsafe content", "garm"] user_level: "Beginner" last_updated: "2025-09-26"
What is this?
The Creator Safety Score is an AI-powered metric that analyses a creator's historical content for any posts that may be considered unsafe or not brand-appropriate, based on the Global Alliance for Responsible Media (GARM) framework.

Why is it useful?
Brand safety is paramount. This score provides a fast and reliable first line of defense in your vetting process. It automates the time-consuming and error-prone task of manually scrolling through a creator's entire history, allowing you to quickly flag any potential risks. This helps you protect your brand's reputation and make more confident partnership decisions.

:---
title: "FAQ: What are Brand Affinities?" doc_id: "faq-005" type: "FAQ" feature_area: ["Creator Profiles"] prerequisites: [] unlocks: [] keywords: ["brand affinity", "competitors", "past partnerships", "brand mentions"] user_level: "Intermediate" last_updated: "2025-09-26"
Question
What does the 'Brand Affinities' section on a Creator Profile tell me?

Answer
The Brand Affinities section shows a list of other brands that the creator has recently mentioned or tagged in their content. This includes both paid partnerships and organic mentions.

Why is it useful?
This data is strategically valuable for two main reasons. First, it is the most effective way to check for potential competitor conflicts. If a creator is actively promoting a direct competitor, they may not be the right fit for your campaign. Second, it can reveal opportunities for complementary partnerships. If a creator frequently mentions brands that align well with yours (e.g., a sustainable fashion creator who also promotes clean beauty brands), it signals a strong alignment in values and audience interests.

:---
title: "FAQ: What is the difference between owned, earned, and paid media in a profile?" doc_id: "faq-006" type: "FAQ" feature_area: ["Creator Profiles"] prerequisites: [] unlocks: [] keywords: ["owned media", "earned media", "paid media", "content types", "media analysis"] user_level: "Intermediate" last_updated: "2025-09-26"
Question
In the 'Media' tab of a Creator Profile, what do the different content types like owned, earned, and paid mean?

Answer
These terms categorise the creator's content based on its context.

Owned Media: This is the creator's own organic content, where they are not being paid to promote a specific product.

Paid Media: This refers to content that is clearly marked as a sponsored post or advertisement. This is content from a formal partnership.

Earned Media: This is when other users or brands mention the creator. It is a measure of their influence and reach within the broader social ecosystem.

Why is it useful?
Analysing the mix of these content types gives you a more nuanced understanding of a creator's strategy. A high volume of high-quality owned media shows a genuine passion for their niche. A high volume of paid media from reputable brands signals that they are a trusted and effective partner. A high volume of earned media indicates that they are influential and respected by their peers.

:---
title: "FAQ: How is the Brand Safety Score Calculated?" doc_id: "faq-008" type: "FAQ" feature_area: ["Creator Profiles"] prerequisites: ["concept-006"] unlocks: [] keywords: ["safety score calculation", "garm", "severity score", "recency", "risk weighting"] user_level: "Intermediate" last_updated: "2025-09-26"
Question
How is the Brand Safety Score calculated and what factors influence it?

Answer
The score is calculated by scanning a creator's last 30 captions with our in-house model trained on GARM standards. The model flags content across key risk categories and assigns a severity score.
The final score is influenced by several factors:

Severity of Flagged Content: Posts are scored as Mild (0.3), Moderate (0.7), or Severe (1.0).

Category Risk Weighting: Different content categories carry different weights. For example, Hate Speech and Terrorism have a weight of 1.00, while Obscenity & Profanity is lower at 0.50.

Recency of Posts: More recent flagged content has a higher impact. A post from 0-3 months ago has a recency factor of 1.0, which decreases over time.

Context and Sentiment: The model attempts to account for the intent and tone of content (e.g., educational, satirical), which can adjust category weights for certain posts to avoid misclassification.

:---
title: "FAQ: Understanding the Nuances of the Brand Safety Score" doc_id: "faq-009" type: "FAQ" feature_area: ["Creator Profiles"] prerequisites: ["faq-008"] unlocks: [] keywords: ["safety score details", "zero score", "severe posts", "older content", "contextual nuance", "flagged posts"] user_level: "Advanced" last_updated: "2025-09-26"
Question
What are some important details to know about interpreting the Brand Safety Score?

Answer
The Brand Safety Score is a powerful tool, but it's important to understand its nuances to use it effectively.

Common Questions & Pitfalls
Why is the score zero? A single post categorised as "Severe" in a "Very High" risk category (like Hate Speech) will result in a score of 0. This is a deliberate design choice to ensure zero tolerance for maximally unsafe content.

How is older content handled? While we emphasize recent content, older flagged posts (up to 24+ months) still contribute to the score, although with a significantly lower weight. This ensures past egregious content is not completely ignored.

Is the model's context analysis perfect? While we strive to account for intent and tone (e.g., educational, satirical), there might be edge cases where content is still flagged due to keyword presence. We are continuously working to improve this.

Can I see which posts were flagged? Yes, you will be able to view the specific posts that were flagged, their categories, and their severity, allowing for full transparency and manual review. This is crucial for making a final, informed decision.