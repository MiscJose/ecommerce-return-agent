let configPromise: Promise<string> | null = null

export function getApiUrl(): Promise <string> {
    if (!configPromise) {
        configPromise = fetch('/config.json')
            .then(response => response.json())
            .then(config => config['API_URL'])
    }

    return configPromise
}