class App {
    constructor(baseURL, maxNgrams) {
        this.baseURL = baseURL;
        this.maxNgrams = 2;
    }
    index() {
        let that = this;
        const searchForm = document.querySelector("#searchForm");
        const article = document.querySelector("article");
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
                    console.log('success:', result);
                    article.replaceChildren(); // remove old paragraphs
                    article.dataset.id = result.id;
                    result.lines.forEach(line => {
                        const p = document.createElement("p");
                        line.forEach(token => {
                            let span = document.createElement("span");
                            span.className = "main"
                            p.append(span);

                            const space = document.createTextNode(" ");
                            p.append(space);
                            for (let i = 1; i < that.maxNgrams; i++) {
                                let nextSpan = document.createElement("span");
                                span.append(nextSpan);
                                span = nextSpan;
                            }
                            const spanContent = document.createTextNode(token);
                            span.append(spanContent);
                        });
                        article.append(p);
                    });
                })
                .catch(error => {
                    console.error('error:', error);
                });
        });

        const algorithmSelector = document.querySelector("#algorithmSelector");
        algorithmSelector.addEventListener("submit", event => {
            event.preventDefault();
            const formData = new FormData(algorithmSelector);
            if (formData.get('algorithm') === '') {
                return;
            }
            const requestURL = new URL('/api/candidateLabels/' + article.dataset.id, that.baseURL);
            requestURL.searchParams.append('algorithm', formData.get('algorithm'));
            fetch(requestURL.href, {
                method: 'GET'
            })
                .then(response => response.json())
                .then(result => {
                    console.log('success:', result);
                    result.forEach(label => {
                        const line = article.querySelectorAll("p")[label.line];
                        const span = line.querySelectorAll("span.main")[label.start];
                        if (label.ngrams === 1) {
                            span.style.borderBottom = "1px solid red";
                        } else if (label.ngrams === 2) {
                            console.log(label);
                            span.querySelector("span").style.borderBottom = "1px solid blue";
                            span.querySelector("span").style.paddingBottom = "3px";
                        }
                    });
                })
                .catch(error => {
                    console.error('error:', error);
                });
        });
    }
}