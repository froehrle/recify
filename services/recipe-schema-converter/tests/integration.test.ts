/**
 * Integration test for Recipe Schema Converter
 * Tests the full conversion pipeline with a real Instagram recipe post.
 */

import { describe, it, expect, beforeAll } from "bun:test";
import { RecipeConverter } from "../src/converter.ts";
import type { RawRecipeData, StructuredRecipe } from "../src/types/index.ts";

describe("RecipeConverter Integration", () => {
  let converter: RecipeConverter;

  beforeAll(() => {
    // Ensure GITHUB_TOKEN is set
    if (!process.env.GITHUB_TOKEN) {
      throw new Error(
        "GITHUB_TOKEN environment variable is required for integration tests"
      );
    }
    converter = new RecipeConverter();
  });

  it("should convert German tofu wrap recipe to structured format", async () => {
    // Real Instagram post: Tofu-Hack Wraps (German recipe)
    const rawRecipeData: RawRecipeData = {
      url: "https://www.instagram.com/p/DITcnygqFll/",
      caption:
        "Du brauchst kein Fleisch, um Biss und Geschmack zu haben – dieser Tofu-Hack beweist's. 🔥\n\n🍽️Portionen: 1 - 2 Wraps | 🔥Schwierigkeitsgrad: einfach\n\n📃ZUTATEN\nFür das Tofu-Hack:\n400 g Naturtofu\n2 EL Tomatenmark\n4 EL dunkle Sojasߟe (alternativ helle)\n1 TL getrockneter Oregano\n1 TL Paprikapulver (edelsüß oder geräuchert)\nSalz und Pfeffer\n1 EL neutrales Öl\nTortilla Wrap\n\nFür die Guacamole:\n1 Avocado\nEtwas Zitronensaft\nEtwas Salz\n\nFür die Tomatensalsa:\n2 Tomaten\n1 rote Zwiebel\n1 Handvoll Koriander oder Petersilie\n1 EL Zitronensaft\nEtwas Salz\n\n👨🏽‍🍳 ZUBEREITUNG\n1. Tofumarinade vorbereiten: Tomatenmark mit Sojasߟe, Oregano, Paprikapulver, Salz, Pfeffer und Öl in einer Schüssel glatt rühren.\n2. Tofu vorbereiten: Den Naturtofu mit einem Küchentuch trocken tupfen, fein zerbröѕeln und in die Marinade geben. Gut vermengen und einige Minuten ziehen lassen.\n3. Tofu backen: Die marinierten Tofubröѕel entweder:\u2028– im Airfryer bei 180 °C für ca. 20 Minuten backen, dabei alle 5 Minuten umrühren, oder\u2028– im Backofen bei ca. 200 °C (Ober-/Unterhitze) für 25–30 Minuten backen, ebenfalls gelegentlich wenden.\u2028Ziel: knusprig gebräunte, leicht karamellisierte Tofubröѕel.\n4. Salsa & Guacamole zubereiten: Tomaten und Zwiebel würfeln, Kräuter hacken, alles mit Zitronensaft und Salz vermischen. Avocado mit Zitronensaft und Salz zerdrücken.\n5. Wraps füllen und genießen: Die Avocadocreme auf einem Wrap verstreichen, das Tofu-Hack und die frische Salsa daraufgeben, einrollen – und genießen!\n\n#tofu",
      media_urls: [
        "https://scontent-ber1-1.cdninstagram.com/o1/v/t2/f2/m367/AQNaiWS-oxiVzxiuNU8hAvInJcVHbuK76RRIVecfuuFBI4GCt8sEp6f2h-JKEFcbJIa91kxY2t5ibhY8wwOf3TR-ltwAdUCucmNGLNA.mp4?_nc_cat=107&_nc_sid=5e9851&_nc_ht=scontent-ber1-1.cdninstagram.com&_nc_ohc=3sR6PbfFC2sQ7kNvwFLUfji&efg=eyJ2ZW5jb2RlX3RhZyI6Inhwdl9wcm9ncmVzc2l2ZS5JTlNUQUdSQU0uQ0xJUFMuQzMuNzIwLmRhc2hfYmFzZWxpbmVfMV92MSIsInhwdl9hc3NldF9pZCI6MzgxMzkwNjAyODkyMjU3NywiYXNzZXRfYWdlX2RheXMiOjI1MCwidmlfdXNlY2FzZV9pZCI6MTAwOTksImR1cmF0aW9uX3MiOjM5LCJ1cmxnZW5fc291cmNlIjoid3d3In0%3D&ccb=17-1&_nc_gid=QUmgAiLM6anc86tGI5OjUQ&_nc_zt=28&vs=bcf10ccf8c50cb8e&_nc_vs=HBksFQIYQGlnX2VwaGVtZXJhbC9GMzQxMjIxNTVEMUNBQTlENzA5RjVEODg2OEIwNUU4Nl92aWRlb19kYXNoaW5pdC5tcDQVAALIARIAFQIYOnBhc3N0aHJvdWdoX2V2ZXJzdG9yZS9HTGE1TVIzMkJ3aDQ4LVFCQUhOQ05lcWZGTWhqYnFfRUFBQUYVAgLIARIAKAAYABsCiAd1c2Vfb2lsATEScHJvZ3Jlc3NpdmVfcmVjaXBlATEVAAAmopv8oMauxg0VAigCQzMsF0BD8KPXCj1xGBJkYXNoX2Jhc2VsaW5lXzFfdjERAHX-B2XmnQEA&oh=00_AfmeCtccYlMzO-A8bkLsvBnSwT6zErPEjn9UnUIeMWhnPw&oe=6948C158",
      ],
      author: "veganewunder",
      timestamp: "2025-04-11T11:02:24",
      hashtags: ["tofu"],
      mentions: [],
      likes_count: 36903,
      comments_count: 104,
      author_top_comment: null,
    };

    // Convert to structured recipe
    const result: StructuredRecipe = await converter.convert(rawRecipeData);

    // Log the full result for inspection
    console.log("\n📋 Structured Recipe Output:");
    console.log(JSON.stringify(result, null, 2));

    // Validate schema.org structure
    expect(result["@context"]).toBe("https://schema.org");
    expect(result["@type"]).toBe("Recipe");

    // Validate required fields
    expect(result.name).toBeDefined();
    expect(result.name.length).toBeGreaterThan(0);
    expect(result.source_url).toBe(rawRecipeData.url);
    expect(result.extraction_confidence).toBeGreaterThanOrEqual(0);
    expect(result.extraction_confidence).toBeLessThanOrEqual(1);

    // Validate author
    expect(result.author).toBeDefined();
    expect(result.author?.["@type"]).toBe("Person");
    expect(result.author?.name).toBe("veganewunder");
    expect(result.author?.url).toBe("https://www.instagram.com/veganewunder");

    // Validate metadata
    expect(result.datePublished).toBe(rawRecipeData.timestamp);
    expect(result.image).toEqual(rawRecipeData.media_urls);
    expect(result.keywords).toContain("tofu");

    // Validate recipe content extraction
    console.log("\n✅ Validation Results:");
    console.log(`- Name: ${result.name}`);
    console.log(
      `- Ingredients: ${result.recipeIngredient?.length || 0} items`
    );
    console.log(
      `- Instructions: ${typeof result.recipeInstructions === "string" ? "text" : Array.isArray(result.recipeInstructions) ? result.recipeInstructions.length + " steps" : "not provided"}`
    );
    console.log(`- Prep Time: ${result.prepTime || "not extracted"}`);
    console.log(`- Cook Time: ${result.cookTime || "not extracted"}`);
    console.log(`- Yield: ${result.recipeYield || "not extracted"}`);
    console.log(`- Category: ${result.recipeCategory || "not extracted"}`);
    console.log(`- Cuisine: ${result.recipeCuisine || "not extracted"}`);
    console.log(`- Confidence: ${result.extraction_confidence}`);

    // Expect ingredients to be extracted (German recipe has clear ingredient list)
    expect(result.recipeIngredient).toBeDefined();
    expect(result.recipeIngredient!.length).toBeGreaterThan(0);

    // Expect instructions to be extracted
    expect(result.recipeInstructions).toBeDefined();

    // Recipe yield should be extracted ("1 - 2 Wraps")
    expect(result.recipeYield).toBeDefined();

    console.log("\n✅ Integration test passed!");
  }, 120000); // 120 second timeout for LLM call
});