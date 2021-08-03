class App {
    constructor(baseURL) {
        this.baseURL = baseURL;
    }
    index() {
        let that = this;
        const searchForm = document.querySelector("#searchForm");
        searchForm.addEventListener("submit", event => {
            event.preventDefault();
            const formData = new FormData(searchForm);
            const requestURL = new URL('/api/article', that.baseURL);
            requestURL.searchParams.append('title', formData.get('title'));
            fetch(requestURL.href, {
                method: 'GET'
            })
                .then(response => response.json())
                .then(result => {
                    console.log('Success:', result);
                })
                .catch(error => {
                    console.error('Error:', error);
                });
        });
    }
}