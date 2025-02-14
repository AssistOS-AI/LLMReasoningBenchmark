const applicationModule = require('assistos').loadModule('application', {});
const personalityModule = require('assistos').loadModule('personality', {});
const documentModule = require('assistos').loadModule('document', {});

import {
    generateProblemDescription,
    generateRandomConfig,
    solveProblem,
    checkUserSolution,
    generatePrologCode
} from "../../libs/starship-transport-generator.js";

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

                const { personality, speciesCount, individualsPerSpecies, relationshipsCount, starshipCapacity, document: documentId } = formData.data;
                console.log('Extracted data:', { personality, speciesCount, individualsPerSpecies, relationshipsCount, starshipCapacity, document: documentId });
                const config = generateRandomConfig(speciesCount, relationshipsCount, starshipCapacity);
                const prologProgram = generatePrologCode(config);
                const prompt = generateProblemDescription(config);
                let analysisData = { personality, speciesCount, individualsPerSpecies, relationshipsCount, starshipCapacity, prompt, config };
                console.log('Running application task with data:', analysisData);
                const taskId = await applicationModule.runApplicationTask(
                    assistOS.space.id,
                    "LLMReasoningBenchmark",
                    "SolveReasoningProblem",
                    analysisData
                );
                console.log('Task created with ID:', taskId);

                await assistOS.UI.closeModal(this.element, taskId);
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