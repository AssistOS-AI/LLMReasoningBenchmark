const LLM_REASONING_DOCUMENT_TITLE = 'llm_reasoning_document';
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
            // Get personality description
            this.logProgress("Fetching personality details...");
            this.logInfo(`Parameters received: ${JSON.stringify(this.parameters)}`);

            const personalityObj = await personalityModule.getPersonality(this.spaceId, this.parameters.personality);
            if (!personalityObj) {
                this.logError("Personality not found by ID");
                throw new Error('Personality not found by ID');
            }

            this.logInfo(`Found personality name: ${personalityObj.name}`);
            if (!personalityObj) {
                this.logError("Personality not found by name");
                throw new Error('Personality not found by name');
            }
            this.logSuccess("Personality details fetched successfully");
            this.logProgress("Constructing analysis prompt...");

            const prompt = this.parameters.prompt;
            this.logSuccess("Successfully generated solution");

            // Save analysis as a document
            this.logProgress("Saving analysis results...");
            // check if document already exists
            const documents = await documentModule.getDocumentsMetadata(this.spaceId);
            const existingDocument = documents.find(doc => doc.title === LLM_REASONING_DOCUMENT_TITLE);
            let documentId;
            if(!existingDocument) {
                const documentObj = {
                    title: LLM_REASONING_DOCUMENT_TITLE,
                    type: TASK_TYPE,
                    content: "",
                    abstract: JSON.stringify({
                        personality: personalityObj.name,
                        timestamp: new Date().toISOString()
                    }, null, 2),
                    metadata: {
                        id: null,  // This will be filled by the system
                        title: LLM_REASONING_DOCUMENT_TITLE
                    }
                };

                documentId = await documentModule.addDocument(this.spaceId, documentObj);
            } else {
                documentId = existingDocument.id;
            }

            this.logProgress("Adding chapters and paragraphs...");
            const chapterIds = [];

            let chapterData = {
                title: new Date().toISOString()
            };

            let chapterId = await documentModule.addChapter(this.spaceId, documentId, chapterData);
            chapterIds.push(chapterId);
            this.logInfo(`Added chapter for current run`, {
                documentId: documentId,
                chapterId: chapterId
            });

            let paragraphObj = {
                text: personalityObj.llms.text
            };

            let paragraphId = await documentModule.addParagraph(this.spaceId, documentId, chapterId, paragraphObj);
            this.logInfo(`Added paragraph for model name`, {
                documentId: documentId,
                chapterId: chapterId,
                paragraphId: paragraphId
            });

            paragraphObj = {
                text: prompt
            };

            paragraphId = await documentModule.addParagraph(this.spaceId, documentId, chapterId, paragraphObj);
            this.logInfo(`Added paragraph for problem statement`, {
                documentId: documentId,
                chapterId: chapterId,
                paragraphId: paragraphId
            });

            paragraphObj = {
                text: "Solution"
            };
            paragraphId = await documentModule.addParagraph(this.spaceId, documentId, chapterId, paragraphObj);

            paragraphObj = {};
            paragraphId = await documentModule.addParagraph(this.spaceId, documentId, chapterId, paragraphObj);
            const config = {
                spaceId: this.spaceId,
                documentId,
                paragraphId,
                prompt,
                agentId: this.parameters.agentId
            }

            await documentModule.chatCompleteParagraph(config);
            this.logInfo(`Added paragraph for solution`, {
                documentId: documentId,
                chapterId: chapterId,
                paragraphId: paragraphId
            });
            this.logSuccess("Successfully added all chapters and paragraphs");
            this.logSuccess(`Analysis saved as document with ID: ${documentId}`);
            return {
                status: 'completed',
                documentId: documentId
            };

        } catch (error) {
            console.error(error);
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