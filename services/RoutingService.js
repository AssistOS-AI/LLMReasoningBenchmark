const LLM_REASONING_BENCHMARK = "llm-reasoning-benchmark";

export class RoutingService {
    constructor() {
        if (RoutingService.instance) {
            return RoutingService.instance;
        } else {
            RoutingService.instance = this;
            return this;
        }
    }

    async navigateToLocation(locationArray = [], appName) {
        if (locationArray.length === 0 || locationArray[0] === LLM_REASONING_BENCHMARK) {
            const pageUrl = `${assistOS.space.id}/${appName}/${LLM_REASONING_BENCHMARK}`;
            await assistOS.UI.changeToDynamicPage(LLM_REASONING_BENCHMARK, pageUrl);
            return;
        }
        if (locationArray[locationArray.length - 1] !== LLM_REASONING_BENCHMARK) {
            console.error(`Invalid URL: URL must end with ${LLM_REASONING_BENCHMARK}`);
            return;
        }
        const webComponentName = locationArray[locationArray.length - 1];
        const pageUrl = `${assistOS.space.id}/${appName}/${locationArray.join("/")}`;
        await assistOS.UI.changeToDynamicPage(webComponentName, pageUrl);
    }

    static async navigateInternal(subpageName, presenterParams) {
        try {
            const pageUrl = `${assistOS.space.id}/LLMReasoningBenchmark/${subpageName}`;
            await assistOS.UI.changeToDynamicPage(subpageName, pageUrl, presenterParams);
        } catch (error) {
            console.error('Navigation error:', error);
            throw error;
        }
    }
} 