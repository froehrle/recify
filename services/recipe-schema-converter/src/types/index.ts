/**
 * Types generated from AsyncAPI specification.
 * These match the exact wire format of messages.
 */

// =============================================================================
// INPUT: RawRecipeData (from raw_recipe_data queue)
// =============================================================================

/**
 * Raw recipe data extracted from Instagram posts.
 * Matches the RawRecipeData message from the instagram-scraper service.
 */
export interface RawRecipeData {
  /** Original Instagram post URL */
  url: string;

  /** Full post caption text (may contain recipe instructions) */
  caption: string;

  /** URLs of all images/videos in the post (including carousel items) */
  media_urls: string[];

  /** Instagram username of the post author */
  author: string;

  /** Post creation timestamp in ISO 8601 format */
  timestamp: string;

  /** List of hashtags used in the post (without # symbol) */
  hashtags: string[];

  /** List of mentioned usernames (without @ symbol) */
  mentions: string[];

  /** Number of likes on the post (null if unavailable) */
  likes_count?: number | null;

  /** Number of comments on the post (null if unavailable) */
  comments_count?: number | null;

  /** Most-liked comment by the post author (often contains recipe details) */
  author_top_comment?: string | null;
}

// =============================================================================
// OUTPUT: StructuredRecipe (to structured_recipes queue)
// =============================================================================

/** A single step in recipe instructions (schema.org/HowToStep) */
export interface HowToStep {
  "@type": "HowToStep";
  text: string;
}

/** Author information (schema.org/Person) */
export interface Person {
  "@type": "Person";
  name: string;
  url?: string;
}

/**
 * Structured recipe in schema.org/Recipe format.
 * @see https://schema.org/Recipe
 */
export interface StructuredRecipe {
  "@context": "https://schema.org";
  "@type": "Recipe";

  /** Recipe title */
  name: string;

  /** Brief description of the recipe */
  description?: string | null;

  /** Recipe author */
  author?: Person;

  /** Publication date in ISO 8601 format */
  datePublished?: string;

  /** Image URLs */
  image?: string[];

  /** List of ingredients */
  recipeIngredient?: string[];

  /** Cooking instructions (text or structured steps) */
  recipeInstructions?: string | HowToStep[];

  /** Preparation time in ISO 8601 duration format (e.g., PT15M) */
  prepTime?: string | null;

  /** Cooking time in ISO 8601 duration format */
  cookTime?: string | null;

  /** Total time in ISO 8601 duration format */
  totalTime?: string | null;

  /** Number of servings or yield */
  recipeYield?: string | null;

  /** Recipe category (appetizer, main, dessert, etc.) */
  recipeCategory?: string | null;

  /** Cuisine type (Italian, Mexican, etc.) */
  recipeCuisine?: string | null;

  /** Comma-separated keywords */
  keywords?: string | null;

  /** Original Instagram post URL */
  source_url: string;

  /** Confidence score of extraction (0-1) */
  extraction_confidence: number;

  /** Notes about what could/could not be extracted */
  extraction_notes?: string | null;
}

// =============================================================================
// LLM Response Types
// =============================================================================

/**
 * Partial recipe data returned by the LLM.
 * All fields are optional since extraction is best-effort.
 */
export interface LLMExtractionResponse {
  name?: string;
  description?: string | null;
  recipeIngredient?: string[];
  recipeInstructions?: string | HowToStep[];
  prepTime?: string | null;
  cookTime?: string | null;
  totalTime?: string | null;
  recipeYield?: string | null;
  recipeCategory?: string | null;
  recipeCuisine?: string | null;
  extraction_confidence?: number;
  extraction_notes?: string | null;
}