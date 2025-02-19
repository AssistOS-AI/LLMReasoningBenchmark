const applicationModule = require('assistos').loadModule('application', {});
const personalityModule = require('assistos').loadModule('personality', {});
const documentModule = require('assistos').loadModule('document', {});
import {
    generateProblemDescription,
    generateRandomConfig,
    checkUserSolution,
    generatePrologCode
} from "../../libs/starship-transport-generator.js";

const LLM_REASONING_DOCUMENT_TITLE = 'llm_reasoning_document';

export class LLMReasoningBenchmarkModal {
    constructor(element, invalidate) {
        this.element = element;
        this.invalidate = invalidate;
        this.documents = [];
        this.currentTheme = localStorage.getItem('theme') || 'light';
        this.invalidate();
    }

    async beforeRender() {
        try {
            // Load personalities from AssistOS
            const personalities = await personalityModule.getPersonalitiesMetadata(assistOS.space.id);
            console.log('Number of personalities:', personalities.length);
            this.personalities = personalities;
            this.personalityOptions = personalities.map(personality => {
                return `<option value="${personality.id}">${personality.name}</option>`;
            });

            // Load documents from AssistOS
            const documents = await documentModule.getDocumentsMetadata(assistOS.space.id);
            console.log('Number of documents:', documents.length);
            console.log('Documents:', documents);
            this.documents = documents;
            this.documentOptions = documents.map(doc => {
                const title = doc.title || doc.name || doc.id;
                return `<option value="${doc.id}">${title}</option>`;
            });
        } catch (error) {
            console.error('Error loading data:', error);
            this.personalityOptions = [];
            this.documentOptions = [];
        }
    }

    async afterRender() {
        this.setupEventListeners();
        document.addEventListener('themechange', this.handleThemeChange.bind(this));
    }

    async closeModal(_target, taskId) {
        await assistOS.UI.closeModal(_target, taskId);
    }

    setupEventListeners() {
        const form = this.element.querySelector('#llmBenchmarkForm');
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            await this.handleAnalysis(form);
        });
    }

    async extractDocumentContent(document) {
        if (!document) return '';
        if (document.content) return document.content;
        if (document.chapters) {
            return document.chapters
                .map(chapter => {
                    const texts = [];
                    if (chapter.title) texts.push(`Chapter: ${chapter.title}`);
                    if (chapter.paragraphs) {
                        texts.push(chapter.paragraphs
                            .filter(p => p && p.text)
                            .map(p => p.text)
                            .join('\n\n'));
                    }
                    return texts.filter(t => t && t.trim()).join('\n\n');
                })
                .filter(t => t && t.trim())
                .join('\n\n');
        }
        return '';
    }

    extractArrayFromString(str) {
        // Regular expression to find the array.
        const regex = /\[\s*("[^"]*"(?:\s*,\s*"[^"]*")*)\s*\]/;

        const match = str.match(regex);

        if (match && match[1]) {
            // Construct a valid JSON string.
            const jsonString = `[${match[1]}]`;
            const array = JSON.parse(jsonString);
            return array;
        } else {
            throw new Error("No array found in the string.");
        }
    }

    async logTaskStatus(taskStatus) {
        console.log('Task status:', taskStatus);
        if (taskStatus === 'completed') {
            const documents = await documentModule.getDocumentsMetadata(assistOS.space.id);
            this.documentId = documents.find(doc => doc.title === LLM_REASONING_DOCUMENT_TITLE).id;
            const document = await documentModule.getDocument(assistOS.space.id, this.documentId);
            console.log('Document items:', document);
            console.log(this.prologProgram);
            let solutionIsValid = false;
            console.log(JSON.stringify(this.config, null, 2));
            let lastChapter = document.chapters[document.chapters.length - 1];
            const lastParagraph = lastChapter.paragraphs[lastChapter.paragraphs.length - 1];
            try {
                let solution = lastParagraph.text;
                console.log('Solution before:', solution);
                // extract from solution only the json object of the solution which is inside []
                solution = this.extractArrayFromString(solution);
                console.log('Solution after:', solution);
                solutionIsValid = await checkUserSolution(this.prologProgram, this.config, solution);
            } catch (e) {
                console.error('Error checking solution:', e);
                solutionIsValid = false;
            }
            console.log('Solution is valid:', solutionIsValid);
            let paragraphObj = {};
            if (solutionIsValid) {
                paragraphObj = {
                    text: `The solution provided is correct.`
                };
            } else {
                paragraphObj = {
                    text: `The solution provided is incorrect.`
                };
            }

            await documentModule.addParagraph(assistOS.space.id, this.documentId, lastChapter.id, paragraphObj);
            this.invalidate();
        }
    }

    async handleAnalysis(form) {
        try {
            console.log('Starting analysis...');
            await assistOS.loadifyFunction(async () => {
                console.log('Extracting form data...');
                const formData = await assistOS.UI.extractFormInformation(form);
                console.log('Form data:', formData);

                if (!formData.isValid) {
                    console.error('Invalid form data');
                    return assistOS.UI.showApplicationError("Invalid form data", "Please fill all the required fields", "error");
                }

                let {
                    personality,
                    speciesCount,
                    individualsPerSpecies,
                    relationshipsCount,
                    starshipCapacity,
                    document: documentId
                } = formData.data;
                console.log('Extracted data:', {
                    personality,
                    speciesCount,
                    individualsPerSpecies,
                    relationshipsCount,
                    starshipCapacity,
                    document: documentId
                });
                speciesCount = parseInt(speciesCount);
                individualsPerSpecies = parseInt(individualsPerSpecies);
                relationshipsCount = parseInt(relationshipsCount);
                this.config = generateRandomConfig(speciesCount, individualsPerSpecies, relationshipsCount, starshipCapacity);
                this.prologProgram = generatePrologCode(this.config);
                const prompt = generateProblemDescription(this.config);
                let analysisData = {
                    personality,
                    speciesCount,
                    individualsPerSpecies,
                    relationshipsCount,
                    starshipCapacity,
                    prompt,
                    config: this.config,
                    agentId: assistOS.agent.agentData.id
                };
                console.log('Running application task with data:', analysisData);
                this.taskId = await applicationModule.runApplicationTask(
                    assistOS.space.id,
                    "LLMReasoningBenchmark",
                    "SolveReasoningProblem",
                    analysisData
                );
                await assistOS.NotificationRouter.subscribeToSpace(assistOS.space.id, this.taskId, this.logTaskStatus.bind(this));
                console.log('Task created with ID:', this.taskId);
                await assistOS.UI.closeModal(this.element, this.taskId);
            });
        } catch (error) {
            console.error('Error in handleAnalysis:', error);
            assistOS.UI.showApplicationError("Analysis Error", error.message, "error");
        }
    }

    handleThemeChange() {
        this.currentTheme = document.documentElement.getAttribute('theme') || 'light';
        this.invalidate();
    }
} 