class App {
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
}

class Index extends App {
    constructor(baseURL, maxNgrams) {
        super(baseURL, maxNgrams);
        const that = this;
        const searchForm = document.querySelector("#searchForm");
        const algorithmSelector = document.querySelector("#algorithmSelector");

        // load article from get parameter
        if ('title' in that.get) {
            const title = that.get['title'];
            searchForm.querySelector("input[name=title]").value = title;
            that.loadArticle(title).then(() => {
                if ('algorithm' in that.get) {
                    const algorithm = that.get['algorithm'];
                    algorithmSelector.querySelector("select[name=algorithm]").value = algorithm;
                    that.runAlgorithm(algorithm);
                }
            });
        }

        searchForm.addEventListener("submit", event => {
            event.preventDefault();
            const formData = new FormData(searchForm);
            const title = formData.get('title');
            that.loadArticle(title);
        });

        algorithmSelector.addEventListener("submit", event => {
            event.preventDefault();
            const formData = new FormData(algorithmSelector);
            const algorithm = formData.get('algorithm');
            that.runAlgorithm(algorithm);
        });

        // modify EDL on user decision
        document.addEventListener("click",event => {
            if (event.target && event.target.classList.contains("decisionMenuOption")) {
                const radio = event.target;
                const labelIndex = radio.dataset.wikigoldLabel;
                const articleIndex = radio.dataset.wikigoldArticle;
                that.edl[labelIndex].titles[articleIndex].decision = radio.value;
            }
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

    loadArticle(title) {
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

    runAlgorithm(algorithm) {
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
                that.edl.forEach((label, label_index) => {
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

                        let popoverHtml = '<div class="row">' +
                            '<div class="col-4"></div>' +
                            '<div class="col-2 text-center">Correct</div>' +
                            '<div class="col-3 text-center">Incorrect</div>' +
                            '<div class="col-3 text-center">Don\'t known</div>' +
                            '</div>';
                        label.titles.forEach((article, article_index) => {
                            popoverHtml += '<div class="row decisionMenuRow">' +
                                    '<div class="col-4">' +
                                    '<label for="decisionMenuOption" class="col-form-label">' + article.title +'</label>' +
                                    '</div>' +
                                    '<div class="col-2 text-center">' +
                                    '<input class="form-check-input decisionMenuOption" ' +
                                            'name="decisionMenuOption_' + label_index + '_' + article_index + '" ' +
                                            'value="0" data-wikigold-label="' + label_index + '" ' +
                                            'data-wikigold-article="' + article_index + '" type="radio">' +
                                    '</div>' +
                                    '<div class="col-3 text-center">' +
                                    '<input class="form-check-input decisionMenuOption" ' +
                                            'name="decisionMenuOption_' + label_index + '_' + article_index + '" ' +
                                            'value="1" data-wikigold-label="' + label_index + '" ' +
                                            'data-wikigold-article="' + article_index + '" type="radio">' +
                                    '</div>' +
                                    '<div class="col-3 text-center">' +
                                    '<input class="form-check-input decisionMenuOption" ' +
                                            'name="decisionMenuOption_' + label_index + '_' + article_index + '" ' +
                                            'value="2" data-wikigold-label="' + label_index + '" ' +
                                            'data-wikigold-article="' + article_index + '" type="radio">' +
                                    '</div>' +
                                '</div>';
                        });

                        // create popovers
                        const popover = new bootstrap.Popover(span, {
                            "title": label.name,
                            "html": true,
                            "sanitize": false,
                            "content": popoverHtml,
                            "placement": "bottom",
                            "trigger": "manual",
                            "template": '<div class="popover ngram_popover_' + label.ngrams + '" role="tooltip">' +
                                '<div class="popover-arrow"></div>' +
                                '<h3 class="popover-header"></h3>' +
                                '<div class="popover-body"></div>' +
                                '</div>'
                        });

                        // only one popover at time - stop event propagation
                        span.addEventListener('click', event => {
                            // check if ngram is active
                            if (span.classList.contains('ngram_link')) {
                                event.stopPropagation();
                                popover.toggle();
                            }
                        });
                        // fill the values of form with the EDL
                        span.addEventListener('shown.bs.popover', event => {
                            const decisions = that.edl[label_index];
                            const popoverElement = popover.getTipElement();
                            popoverElement.querySelectorAll(".decisionMenuRow").forEach((articleRow, articleIndex) => {
                                const decision = decisions.titles[articleIndex].decision;
                                if (decision !== null) {
                                    articleRow.querySelector('input[value="' + decision + '"]').checked = true;
                                }
                            });
                        });

                    });
                });
            })
            .catch(error => {
                console.error('error:', error);
            });
    }
}