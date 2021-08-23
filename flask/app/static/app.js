class App {
    'use strict';
    constructor(baseURL, maxNgrams) {
        this.baseURL = baseURL;
        this.maxNgrams = maxNgrams;
        this.get = {};
        // https://stackoverflow.com/questions/12049620/how-to-get-get-variables-value-in-javascript
        if (document.location.toString().indexOf('?') !== -1) {
            const query = document.location
                   .toString()
                   // get the query string
                   .replace(/^.*?\?/, '')
                   // and remove any existing hash string (thanks, @vrijdenker)
                   .replace(/#.*$/, '')
                   .split('&');

            query.forEach(uriElement => {
                const uriElementDecoded = decodeURIComponent(uriElement).split('=');
                this.get[uriElementDecoded[0]] = uriElementDecoded[1];
            });
        }
    }
    index() {
        const that = this;
        const article = document.querySelector("article");
        const searchForm = document.querySelector("#searchForm");
        const algorithmSelector = document.querySelector("#algorithmSelector");

        // load article from get parameter
        if ('title' in that.get) {
            const title = that.get['title'];
            searchForm.querySelector("input[name=title]").value = title;
            that.indexLoadArticle(title).then(() => {
                if ('algorithm' in that.get) {
                    const algorithm = that.get['algorithm'];
                    algorithmSelector.querySelector("select[name=algorithm]").value = algorithm;
                    that.indexRunAlgorithm(algorithm);
                }
            });
        }

        searchForm.addEventListener("submit", event => {
            event.preventDefault();
            const formData = new FormData(searchForm);
            const title = formData.get('title');
            that.indexLoadArticle(title);
        });

        algorithmSelector.addEventListener("submit", event => {
            event.preventDefault();
            const formData = new FormData(algorithmSelector);
            const algorithm = formData.get('algorithm');
            that.indexRunAlgorithm(algorithm);
        });

        const ngramLinks = document.querySelectorAll(".ngram_link");
        ngramLinks.forEach(ngramLink => {
            ngramLink.addEventListener("click", event => {
                const ngramLink = event.target;
                // const decisionMenu = document.createElement("div");
                // decisionMenu.id = "decisionMenu";
                // decisionMenu.style.position = "absolute";
                //
                // decisionMenu.textContent = 'Mongo!';
                // document.append(decisionMenu);
            });
        });

        const ngramsDisplayCheckboxes = document.querySelectorAll("#ngramsDisplay input");
        ngramsDisplayCheckboxes.forEach(checkbox => {
            checkbox.addEventListener("change", event => {
                const ngram = event.target.value;
                if (event.target.checked) {
                    // show links
                    document.querySelectorAll(".ngram_link_" + ngram).forEach(ngramSpan => {
                        ngramSpan.classList.add("ngram_link");
                    });
                } else {
                    // hide links
                    document.querySelectorAll(".ngram_link_" + ngram).forEach(ngramSpan => {
                        ngramSpan.classList.remove("ngram_link");
                    });
                }
            });
        });
    }

    indexLoadArticle(title) {
        const that = this;
        const article = document.querySelector("article");
        const requestURL = new URL('/api/article', that.baseURL);
        requestURL.searchParams.append('title', title);

        return fetch(requestURL.href, {
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
                        span.classList.add("main");
                        p.append(span);

                        let space = document.createElement("span");
                        p.append(space);

                        for (let i = 1; i < that.maxNgrams; i++) {
                            let nextSpan = document.createElement("span");
                            span.append(nextSpan);
                            span = nextSpan;

                            let nextSpace = document.createElement("span");
                            space.append(nextSpace);
                            space = nextSpace;
                        }
                        const spanContent = document.createTextNode(token);
                        span.append(spanContent);
                        const spaceContent = document.createTextNode(" ");
                        space.append(spaceContent);
                    });
                    article.append(p);
                });
            })
            .catch(error => {
                console.error('error:', error);
            });
    }

    indexRunAlgorithm(algorithm) {
        const that = this;
        const article = document.querySelector("article");

        if (algorithm === '') {
            return;
        }
        const requestURL = new URL('/api/candidateLabels/' + article.dataset.id, that.baseURL);
        requestURL.searchParams.append('algorithm', algorithm);
        return fetch(requestURL.href, {
            method: 'GET'
        })
            .then(response => response.json())
            .then(result => {
                console.log('success:', result);
                that.edl = result;
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
                        span.classList.add("ngram_link");
                        span.classList.add("ngram_link_" + label.ngrams);

                        let popoverHtml = '<form><div class="row g-3 align-items-center">';
                        label.titles.forEach(article => {
                            popoverHtml += '<div class="col-auto">';
                            popoverHtml += '<label for="inputPassword6" class="col-form-label">' + article.title +'</label>';
                            popoverHtml += '</div>';
                            popoverHtml += '<div class="col-auto">';
                            popoverHtml += '<input class="form-check-input" type="checkbox">';
                            popoverHtml += '</div>';
                            popoverHtml += '<div class="col-auto">';
                            popoverHtml += '<input class="form-check-input" type="checkbox">';
                            popoverHtml += '</div>';
                        });
                        popoverHtml += '</div></form>';
                        console.log(popoverHtml);

                        // create popovers
                        const popover = new bootstrap.Popover(span, {
                            "html": true,
                            "content": popoverHtml,
                            "placement": "bottom"
                        });
                    });
                });
            })
            .catch(error => {
                console.error('error:', error);
            });
    }
}