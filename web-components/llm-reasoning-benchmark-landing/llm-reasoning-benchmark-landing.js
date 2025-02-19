import {RoutingService} from "../../services/RoutingService.js";

const personalityModule = require('assistos').loadModule('personality', {});
const documentModule = require('assistos').loadModule('document', {});
const LLM_REASONING_DOCUMENT_TITLE = 'llm_reasoning_document';

export class LLMReasoningBenchmarkLanding {
    constructor(element, invalidate) {
        this.element = element;
        this.invalidate = invalidate;
        this.documents = [];
        this.currentTheme = localStorage.getItem('theme') || 'light';
        this.refreshDocuments = async () => {
            const documentsMetadata = await assistOS.space.getDocumentsMetadata(assistOS.space.id);
            const llmReasoningBenchmarkDocument = documentsMetadata.find((doc) => doc.title.startsWith(LLM_REASONING_DOCUMENT_TITLE));
            if (llmReasoningBenchmarkDocument) {
                this.document = await documentModule.getDocument(assistOS.space.id, llmReasoningBenchmarkDocument.id);
            }
        }
        this.invalidate(async () => {
            await this.refreshDocuments();
            this.boundsOnListUpdate = this.onListUpdate.bind(this);
        });
    }

    onListUpdate() {
        this.invalidate(this.refreshDocuments);
    }

    async beforeRender() {
        this.tableRows = "";

        // Generate rows for bias analysis documents
        const doc = this.document;
        let abstract = {};
        try {
            if (typeof doc.abstract === 'string') {
                const textarea = document.createElement('textarea');
                textarea.innerHTML = doc.abstract;
                let decodedAbstract = textarea.value;
                decodedAbstract = decodedAbstract
                    .replace(/\n/g, '')
                    .replace(/\r/g, '')
                    .replace(/\s+/g, ' ')
                    .trim();
                abstract = JSON.parse(decodedAbstract);
            } else if (doc.abstract && typeof doc.abstract === 'object') {
                abstract = doc.abstract;
            }
        } catch (error) {
            console.error('Error handling abstract:', error);
        }

        const timestamp = abstract.timestamp ? new Date(abstract.timestamp).toLocaleString() : 'N/A';
        if(doc) {
            this.tableRows = `
                <div class="analysis-card" data-id="${doc.id}">
                    <div class="analysis-content" data-local-action="viewAnalysis">
                        <h3>${doc.title}</h3>
                        <div class="analysis-meta">
                            <span class="timestamp">
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                    <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                                    <path d="M12 6v6l4 2" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                                </svg>
                                ${timestamp}
                            </span>
                        </div>
                    </div>
                </div>`;

            if (assistOS.space.loadingDocuments) {
                assistOS.space.loadingDocuments.forEach((taskId) => {
                    this.tableRows = `
                    <div data-id="${taskId}" class="analysis-card placeholder-analysis">
                        <div class="loading-icon small"></div>
                    </div>`;
                });
            }
        }
        if (this.tableRows === "") {
            this.tableRows = `<div class="no-analyses">No analyses found</div>`;
        }
    }

    async afterRender() {
        // Setup any event listeners or post-render operations
        const analysisItems = this.element.querySelectorAll('.analysis-card');
        analysisItems.forEach(item => {
            const content = item.querySelector('.analysis-content');
            if (content) {
                content.addEventListener('click', async () => {
                    // Get the parent card element which has the data-id
                    const card = content.closest('.analysis-card');
                    await this.editAction(card);
                });
            }
        });
        document.addEventListener('themechange', this.handleThemeChange.bind(this));
    }

    handleThemeChange() {
        this.currentTheme = document.documentElement.getAttribute('theme') || 'light';
        this.invalidate();
    }

    async editAction(_target) {
        let documentId = this.getDocumentId(_target);
        await assistOS.UI.changeToDynamicPage("space-application-page", `${assistOS.space.id}/Space/document-view-page/${documentId}`);
    }


    getDocumentId(_target) {
        return _target.getAttribute('data-id');
    }

    async openLLMReasoningBenchmarkModal() {
        const taskId = await assistOS.UI.showModal("llm-reasoning-benchmark-modal", {
            "presenter": "llm-reasoning-benchmark-modal"
        }, true);
        if (taskId) {
            assistOS.watchTask(taskId);
        }
    }
}