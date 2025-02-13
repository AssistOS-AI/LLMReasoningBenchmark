import {RoutingService} from "../../services/RoutingService.js";

const personalityModule = require('assistos').loadModule('personality', {});
const documentModule = require('assistos').loadModule('document', {});
const LLM_REASONING_BENCHMARK_PREFIX = 'llm_reasoning_benchmark_';
export class LlmReasoningBenchmarkLanding {
    constructor(element, invalidate) {
        this.element = element;
        this.invalidate = invalidate;
        this.documents = [];
        this.currentTheme = localStorage.getItem('theme') || 'light';
        this.refreshDocuments = async () => {
            const documentsMetadata = await assistOS.space.getDocumentsMetadata(assistOS.space.id);

            // Filter bias analysis documents
            const llmReasoningBenchmarkDocuments = documentsMetadata.filter((doc) => doc.title.startsWith(LLM_REASONING_BENCHMARK_PREFIX)) || [];

            // Get complete documents with all metadata
            this.documents = await Promise.all(
                llmReasoningBenchmarkDocuments.map(async (doc) => {
                    const fullDoc = await documentModule.getDocument(assistOS.space.id, doc.id);
                    return {
                        ...doc,
                        ...fullDoc,
                        metadata: fullDoc.metadata || {}
                    };
                })
            );
        };
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
        this.documents.forEach((doc) => {
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
            const personality = abstract.personality || 'N/A';

            this.tableRows += `
                <div class="analysis-card" data-id="${doc.id}">
                    <div class="analysis-content" data-local-action="viewAnalysis">
                        <h3>${doc.title}</h3>
                        <div class="analysis-meta">
                            <span class="personality">
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                                    <circle cx="12" cy="7" r="4" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                                </svg>
                                ${personality}
                            </span>
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
        });

        if (assistOS.space.loadingDocuments) {
            assistOS.space.loadingDocuments.forEach((taskId) => {
                this.tableRows += `
                    <div data-id="${taskId}" class="analysis-card placeholder-analysis">
                        <div class="loading-icon small"></div>
                    </div>`;
            });
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

    async deleteAction(_target) {
        let message = "Are you sure you want to delete this analysis?";
        let confirmation = await assistOS.UI.showModal("confirm-action-modal", {message}, true);
        if (!confirmation) {
            return;
        }
        await documentModule.deleteDocument(assistOS.space.id, this.getDocumentId(_target));
        this.invalidate(this.refreshDocuments);
    }

    getDocumentId(_target) {
        return _target.getAttribute('data-id');
    }

    async openBiasDetectorModal() {
        const taskId = await assistOS.UI.showModal("llm-reasoning-benchmark-modal", {
            "presenter": "llm-reasoning-benchmark-modal"
        }, true);
        if (taskId) {
            assistOS.watchTask(taskId);
        }
    }
}