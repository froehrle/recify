/**
 * LLM prompt templates for recipe extraction.
 */

import type { RawRecipeData } from "./types/index.ts";

/**
 * System prompt that establishes the LLM's role and output format.
 */
export const RECIPE_EXTRACTION_SYSTEM_PROMPT = `You are a recipe extraction specialist. Your task is to extract structured recipe information from Instagram post captions.

## Guidelines

1. **Extract what you can confidently identify** - only include fields you're confident about
2. **Ingredients**: Look for lists (bullet points, numbered, comma-separated)
3. **Instructions**: Look for numbered steps, paragraphs describing the cooking process
4. **Times**: Convert mentions like "30 minutes" to ISO 8601 duration format:
   - Minutes: PT15M, PT30M
   - Hours: PT1H, PT2H
   - Combined: PT1H30M
5. **Servings**: Look for phrases like "serves 4", "makes 12", "for 2 people"
6. **Cuisine**: Infer from ingredients, cooking methods, and hashtags
7. **Category**: Determine if it's appetizer, main course, dessert, snack, beverage, etc.

## Output Format

Return a valid JSON object with these fields (omit fields you cannot determine):

\`\`\`json
{
  "name": "Recipe title",
  "description": "Brief description",
  "recipeIngredient": ["ingredient 1", "ingredient 2"],
  "recipeInstructions": [
    {"@type": "HowToStep", "text": "Step 1"},
    {"@type": "HowToStep", "text": "Step 2"}
  ],
  "prepTime": "PT15M",
  "cookTime": "PT30M",
  "totalTime": "PT45M",
  "recipeYield": "4 servings",
  "recipeCategory": "main course",
  "recipeCuisine": "Italian",
  "extraction_confidence": 0.85,
  "extraction_notes": "Could not determine exact cooking time"
}
\`\`\`

## Confidence Score

Set \`extraction_confidence\` based on how complete the recipe information is:
- 0.9-1.0: Complete recipe with ingredients, instructions, and timing
- 0.7-0.9: Good recipe with most key information
- 0.5-0.7: Partial recipe, missing some important details
- 0.3-0.5: Minimal recipe information extracted
- 0.0-0.3: Very little useful recipe data found

## Important

- Return ONLY the JSON object, no additional text
- Use null for fields that cannot be extracted with confidence
- For recipeInstructions, prefer structured HowToStep format when steps are clear`;

/**
 * Build the user prompt with the raw recipe data.
 */
export function buildExtractionPrompt(rawData: RawRecipeData): string {
  const parts: string[] = [
    "Extract recipe information from this Instagram post:",
    "",
    "## Caption",
    rawData.caption,
  ];

  // Include author's top comment if available (often contains recipe details)
  if (rawData.author_top_comment) {
    parts.push("", "## Author's Comment", rawData.author_top_comment);
  }

  // Include hashtags for context
  if (rawData.hashtags.length > 0) {
    parts.push("", "## Hashtags", rawData.hashtags.join(", "));
  }

  // Metadata
  parts.push(
    "",
    "## Metadata",
    `- Author: ${rawData.author}`,
    `- Posted: ${rawData.timestamp}`,
    `- URL: ${rawData.url}`
  );

  parts.push("", "Please extract the recipe details and return as JSON.");

  return parts.join("\n");
}