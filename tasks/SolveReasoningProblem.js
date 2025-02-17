const LLM_REASONING_BENCHMARK_PREFIX = 'llm_reasoning_benchmark_';
const TASK_TYPE = "LLMReasoningBenchmark";
module.exports = {
    runTask: async function () {
        try {
            this.logInfo("Initializing Starship Transport Problem Solving Task ...");
            const llmModule = await this.loadModule("llm");
            const personalityModule = await this.loadModule("personality");
            const utilModule = await this.loadModule("util");
            const documentModule = await this.loadModule("document");

            // Helper functions
            const ensureValidJson = async (jsonString, maxIterations = 1, jsonSchema = null, correctExample = null) => {
                const phases = {
                    "RemoveJsonMark": async (jsonString, error) => {
                        if (jsonString.startsWith("```json")) {
                            jsonString = jsonString.slice(7);
                            if (jsonString.endsWith("```")) {
                                jsonString = jsonString.slice(0, -3);
                            }
                        }
                        return jsonString;
                    },
                    "RemoveOutsideJson": async (jsonString, error) => {
                        if (jsonString.includes("```json")) {
                            const parts = jsonString.split("```json");
                            if (parts.length > 1) {
                                jsonString = parts[1];
                                jsonString = jsonString.split("```")[0];
                            }
                        }
                        return jsonString;
                    },
                    "RemoveNewLine": async (jsonString, error) => {
                        return jsonString.replace(/\n/g, "");
                    },
                    "TrimSpaces": async (jsonString, error) => {
                        return jsonString.trim();
                    },
                    "LlmHelper": async (jsonString, error) => {
                        let prompt = `
                         ** Role:**
                           - You are a global expert in correcting an invalid JSON string to a valid JSON string that is parsable by a JSON parser
                         ** Instructions:**
                            - You will be provided with an invalid JSON string that needs to be corrected.
                            - You will be provided with an error message given by the parser that will help you identify the issue in the JSON string.
                            ${jsonSchema ? `- You will be provided with a JSON schema that the corrected JSON string should adhere to.` : ""}
                            ${correctExample ? `- You will be provided with an example of a correct JSON string that adheres to the schema` : ""}

                         ** Input JSON string that needs to be corrected:**
                         "${jsonString}"

                         ** Error message given by the parser:**
                            "${error}"
                            ${jsonSchema ? `** JSON Schema Template:**\n"${jsonSchema}"\n` : ""}
                            ${correctExample ? `** Example of a correct JSON string that adheres to the schema:**\n"${correctExample}"\n` : ""}
                         **Output Specifications:**
                             - Provide the corrected JSON string that is valid and parsable by a JSON parser.
                             - Your answer should not include any code block markers (e.g., \`\`\`json).
                            - Your answer should not include additional text, information, metadata or meta-commentary
                        `;

                        const response = await llmModule.generateText(this.spaceId, prompt, this.parameters.personality);
                        return response.message;
                    }
                };

                const phaseFunctions = Object.values(phases);

                while (maxIterations > 0) {
                    for (const phase of phaseFunctions) {
                        try {
                            JSON.parse(jsonString);
                            return jsonString;
                        } catch (error) {
                            jsonString = await phase(jsonString, error.message);
                        }
                    }
                    maxIterations--;
                }
                throw new Error("Unable to ensure valid JSON after all phases.");
            };

            // Get personality description
            this.logProgress("Fetching personality details...");
            this.logInfo(`Parameters received: ${JSON.stringify(this.parameters)}`);

            const personality = await personalityModule.getPersonality(this.spaceId, this.parameters.personality);
            if (!personality) {
                this.logError("Personality not found by ID");
                throw new Error('Personality not found by ID');
            }

            this.logInfo(`Found personality name: ${personality.name}`);
            const personalityObj = await personalityModule.getPersonalityByName(this.spaceId, personality.name);
            this.logInfo(`Personality object received: ${JSON.stringify(personalityObj)}`);

            if (!personalityObj) {
                this.logError("Personality not found by name");
                throw new Error('Personality not found by name');
            }
            this.logSuccess("Personality details fetched successfully");

            // Construct the analysis prompt
            this.logProgress("Constructing analysis prompt...");
            const prompt = this.parameters.prompt;
            // Get analysis from LLM with retries
            let response;
            let result;

            const getLLMResponseWithTimeout = async (prompt, timeout = 20000) => {
                return Promise.race([
                    llmModule.generateText(this.spaceId, prompt, personalityObj.id),
                    new Promise((_, reject) =>
                        setTimeout(() => reject(new Error('LLM request timed out')), timeout)
                    )
                ]);
            };

            response = await getLLMResponseWithTimeout(prompt);
            result = response.message;
            console.log("Response:", response);
            this.logSuccess("Successfully generated solution");

            // Save analysis as a document
            this.logProgress("Saving analysis results...");

            const documentObj = {
                title: `${LLM_REASONING_BENCHMARK_PREFIX}${new Date().toISOString()}`,
                type: TASK_TYPE,
                content: JSON.stringify(result, null, 2),
                abstract: JSON.stringify({
                    personality: personalityObj.name,
                    timestamp: new Date().toISOString()
                }, null, 2),
                metadata: {
                    id: null,  // This will be filled by the system
                    title: `${LLM_REASONING_BENCHMARK_PREFIX}}${new Date().toISOString()}`
                }
            };

            const documentId = await documentModule.addDocument(this.spaceId, documentObj);

            this.logProgress("Adding chapters and paragraphs...");
            const chapterIds = [];

            let chapterData = {
                title: `Starship transport problem:`
            };

            let chapterId = await documentModule.addChapter(this.spaceId, documentId, chapterData);
            chapterIds.push(chapterId);
            this.logInfo(`Added chapter for problem`, {
                documentId: documentId,
                chapterId: chapterId
            });

            // Add explanation as paragraph
            let paragraphObj = {
                text: prompt,
            };

            let paragraphId = await documentModule.addParagraph(this.spaceId, documentId, chapterId, paragraphObj);
            this.logInfo(`Added paragraph for solution`, {
                documentId: documentId,
                chapterId: chapterId,
                paragraphId: paragraphId
            });

            chapterData = {
                title: `Solution:`
            };

            chapterId = await documentModule.addChapter(this.spaceId, documentId, chapterData);

            this.logInfo(`Added chapter for solution`);
            paragraphObj = {
                text: result,
            };
            paragraphId = await documentModule.addParagraph(this.spaceId, documentId, chapterId, paragraphObj);
            this.logInfo(`Added paragraph for solution`, {
                documentId: documentId,
                chapterId: chapterId,
                paragraphId: paragraphId
            });
            this.logSuccess("Successfully added all chapters and paragraphs");
            this.logSuccess(`Analysis saved as document with ID: ${documentId}`);
            this.logInfo(`Solution: ${response.message}`);
            return {
                status: 'completed',
                result: response.message,
                documentId: documentId
            };

        } catch (error) {
            this.logError(`Error solving transport problem: ${error.message}`);
            throw error;
        }
    },

    cancelTask: async function () {
        this.logWarning("Task cancelled by user");
    },

    serialize: async function () {
        return {
            taskType: TASK_TYPE,
            parameters: this.parameters
        };
    },

    getRelevantInfo: async function () {
        return {
            taskType: TASK_TYPE,
            parameters: this.parameters
        };
    }
}; 