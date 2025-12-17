/**
 * Recipe Schema Converter Service
 *
 * Consumes raw recipe data from Instagram posts and converts it to
 * structured schema.org/Recipe format using GitHub Models LLM.
 */

import { RecipeConverterWorker } from "./worker.ts";
import {config} from "./config.ts";

async function main() {
  console.log("Recipe Schema Converter Service");
  console.log("================================");
  console.log(`Starting with model: ${config.llm.model}`)

  const worker = new RecipeConverterWorker();
  await worker.start();
}

main().catch((error) => {
  console.error("Fatal error:", error);
  process.exit(1);
});
