/**
 * Recipe converter using GitHub Models (OpenAI-compatible API).
 */

import OpenAI from "openai";
import { config } from "./config.ts";
import {
  RECIPE_EXTRACTION_SYSTEM_PROMPT,
  buildExtractionPrompt,
} from "./prompts.ts";
import type {
  RawRecipeData,
  StructuredRecipe,
  LLMExtractionResponse,
} from "./types/index.ts";

export class RecipeConverter {
  private client: OpenAI;

  constructor() {
    this.client = new OpenAI({
      baseURL: config.llm.baseUrl,
      apiKey: config.llm.apiKey,
    });
  }

  /**
   * Convert raw Instagram recipe data to structured schema.org/Recipe format.
   */
  async convert(rawData: RawRecipeData): Promise<StructuredRecipe> {
    const prompt = buildExtractionPrompt(rawData);

    const response = await this.client.chat.completions.create({
      model: config.llm.model,
      max_completion_tokens: config.llm.maxTokens,
      messages: [
        { role: "system", content: RECIPE_EXTRACTION_SYSTEM_PROMPT },
        { role: "user", content: prompt },
      ],
    });

    const content = response.choices[0]?.message?.content;
    if (!content) {
      throw new Error("No response content from LLM");
    }

    // Parse JSON from response (may be wrapped in markdown code blocks)
    const jsonStr = this.extractJson(content);
    const extracted: LLMExtractionResponse = JSON.parse(jsonStr);

    // Build the final structured recipe
    return this.buildStructuredRecipe(extracted, rawData);
  }

  /**
   * Extract JSON from LLM response, handling markdown code blocks.
   */
  private extractJson(text: string): string {
    // Try to extract from markdown code block
    const codeBlockMatch = text.match(/```(?:json)?\s*([\s\S]*?)```/);
    if (codeBlockMatch?.[1]) {
      return codeBlockMatch[1].trim();
    }

    // Try to find raw JSON object
    const jsonMatch = text.match(/\{[\s\S]*\}/);
    if (jsonMatch) {
      return jsonMatch[0];
    }

    return text.trim();
  }

  /**
   * Build the final StructuredRecipe by merging LLM extraction with source data.
   */
  private buildStructuredRecipe(
    extracted: LLMExtractionResponse,
    rawData: RawRecipeData
  ): StructuredRecipe {
    return {
      "@context": "https://schema.org",
      "@type": "Recipe",
      name: extracted.name || this.inferRecipeName(rawData),
      description: extracted.description ?? null,
      author: {
        "@type": "Person",
        name: rawData.author,
        url: `https://www.instagram.com/${rawData.author}`,
      },
      datePublished: rawData.timestamp,
      image: rawData.media_urls,
      recipeIngredient: extracted.recipeIngredient,
      recipeInstructions: extracted.recipeInstructions,
      prepTime: extracted.prepTime ?? null,
      cookTime: extracted.cookTime ?? null,
      totalTime: extracted.totalTime ?? null,
      recipeYield: extracted.recipeYield ?? null,
      recipeCategory: extracted.recipeCategory ?? null,
      recipeCuisine: extracted.recipeCuisine ?? null,
      keywords: rawData.hashtags.join(", ") || null,
      source_url: rawData.url,
      extraction_confidence: extracted.extraction_confidence ?? 0.5,
      extraction_notes: extracted.extraction_notes ?? null,
    };
  }

  /**
   * Infer recipe name from raw data when LLM doesn't provide one.
   */
  private inferRecipeName(rawData: RawRecipeData): string {
    // Try first line of caption
    const firstLine = rawData.caption.split("\n")[0]?.trim() || "";
    if (firstLine.length > 0 && firstLine.length < 100) {
      // Remove common emojis
      const cleaned = firstLine.replace(/[\u{1F300}-\u{1F9FF}]/gu, "").trim();
      if (cleaned.length > 0) {
        return cleaned;
      }
    }

    // Fall back to first hashtag
    if (rawData.hashtags.length > 0) {
      return rawData.hashtags[0] || "Untitled Recipe";
    }

    return "Untitled Recipe";
  }
}