class App {
    constructor(baseURL, maxNgrams) {
        this.baseURL = baseURL;
        this.maxNgrams = maxNgrams;
        this.colors = ['#00FF00', '#0000FF', '#FF0000', '#01FFFE', '#FFA6FE',
            '#FFDB66', '#006401', '#010067', '#95003A', '#007DB5', '#FF00F6',
            '#FFEEE8', '#774D00', '#90FB92', '#0076FF', '#D5FF00', '#FF937E',
            '#6A826C', '#FF029D', '#FE8900', '#7A4782', '#7E2DD2', '#85A900',
            '#FF0056', '#A42400', '#00AE7E', '#683D3B', '#BDC6FF', '#263400',
            '#BDD393', '#00B917', '#9E008E', '#001544', '#C28C9F', '#FF74A3',
            '#01D0FF', '#004754', '#E56FFE', '#788231', '#0E4CA1', '#91D0CB',
            '#BE9970', '#968AE8', '#BB8800', '#43002C', '#DEFF74', '#00FFC6',
            '#FFE502', '#620E00', '#008F9C', '#98FF52', '#7544B1', '#B500FF',
            '#00FF78', '#FF6E41', '#005F39', '#6B6882', '#5FAD4E', '#A75740',
            '#A5FFD2', '#FFB167', '#009BFF', '#E85EBE'
        ];
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
                            span.style.borderColor = that.colors[0];
                            p.append(span);

                            let space = document.createElement("span");
                            space.style.borderColor = that.colors[0];
                            p.append(space);

                            for (let i = 1; i < that.maxNgrams; i++) {
                                let nextSpan = document.createElement("span");
                                nextSpan.style.paddingBottom = i*3 + "px";
                                nextSpan.style.borderColor = that.colors[i];
                                span.append(nextSpan);
                                span = nextSpan;

                                let nextSpace = document.createElement("span");
                                nextSpace.style.paddingBottom = i*3 + "px";
                                nextSpace.style.borderColor = that.colors[i];
                                space.append(nextSpace);
                                space = nextSpace;
                            }
                            const spanContent = document.createTextNode(token);
                            span.append(spanContent);
                            const spaceContent = document.createTextNode(" ");
                            space.append(spaceContent)
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
                        let span = line.querySelectorAll("span.main")[label.start];
                        const showBorder = [span];
                        // collect spans which should be bordered
                        for (let i = 1; i < label.ngrams; i++){
                            span = span.nextSibling;  // space node
                            showBorder.push(span)
                            span = span.nextSibling; // next token
                            showBorder.push(span)
                        }

                        // select correct level for each span
                        showBorder.forEach(span => {
                            for (let i = 1; i < label.ngrams; i++){
                                span = span.firstChild;
                            }
                            span.style.borderBottomWidth = "1px";
                            span.style.borderBottomStyle = "solid";
                        });
                    });
                })
                .catch(error => {
                    console.error('error:', error);
                });
        });
    }
}