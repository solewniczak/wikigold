class App {
    constructor(baseUrl, maxNgrams) {
        this.baseUrl = baseUrl;
        this.maxNgrams = maxNgrams;
        this.url =  new URL(document.location);
    }
}

class Index extends App {
    constructor(baseUrl, maxNgrams) {
        super(baseUrl, maxNgrams);
        const that = this;
        const searchForm = document.querySelector("#search-form");
        const algorithmSelector = document.querySelector("#algorithm-selector");

        if (that.url.searchParams.has('article')) {
            const articleId = that.url.searchParams.get('article');
            that.loadArticleById(articleId)
                .then(() => that.runAlgorithm());
        }

        searchForm.addEventListener("submit", event => {
            event.preventDefault();
            const formData = new FormData(searchForm);
            const title = formData.get('title');
            that.loadArticleByTitle(title)
                .then(result => {
                    that.url.searchParams.set('article', result.id);
                    that.url.searchParams.delete('algorithm');
                    window.history.replaceState('', '', that.url.href);
                });
        });

        algorithmSelector.addEventListener("submit", event => {
            event.preventDefault();
            const formData = new FormData(algorithmSelector);
            const algorithm = Object.fromEntries(formData);

            that.url.searchParams.set('algorithm', JSON.stringify(algorithm));
            window.history.replaceState('', '', that.url.href);

            that.runAlgorithm();
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

    loadArticleByTitle(title) {
        const that = this;

        const requestURL = new URL('/api/article', that.baseUrl);
        requestURL.searchParams.append('title', title);
        return fetch(requestURL.href, {
            method: 'GET'
        })
            .then(response => response.json())
            .then(result => that.loadArticleFromResult(result));
    }

    loadArticleById(articleId) {
        const that = this;

        const requestURL = new URL('/api/article/' + articleId, that.baseUrl);
        return fetch(requestURL.href, {
            method: 'GET'
        })
            .then(response => response.json())
            .then(result => that.loadArticleFromResult(result));
    }

    loadArticleFromResult(result) {
        const that = this;
        const article = document.querySelector("article");

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
        return result;
    }

    runAlgorithm() {
        const that = this;
        const article = document.querySelector("article");

        const articleId = that.url.searchParams.get('article');
        const algorithm = that.url.searchParams.get('algorithm');

        if (!articleId || !algorithm) return;

        const requestURL = new URL('/api/candidateLabels/' + articleId, that.baseUrl);
        requestURL.searchParams.append('algorithm', algorithm);
        return fetch(requestURL.href, {
            method: 'GET'
        })
            .then(response => response.json())
            .then(result => {
                console.log('success:', result);
                that.edl = result;
                that.edl.forEach((label, labelIndex) => {
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
                        label.titles.forEach((article, articleIndex) => {
                            popoverHtml += '<div class="row decisionMenuRow">' +
                                    '<div class="col-4">' +
                                    '<label for="decisionMenuOption" class="col-form-label">' + article.title +'</label>' +
                                    '</div>' +
                                    '<div class="col-2 text-center">' +
                                    '<input class="form-check-input decisionMenuOption" ' +
                                            'name="decisionMenuOption_' + labelIndex + '_' + articleIndex + '" ' +
                                            'value="0" data-wikigold-label="' + labelIndex + '" ' +
                                            'data-wikigold-article="' + articleIndex + '" type="radio">' +
                                    '</div>' +
                                    '<div class="col-3 text-center">' +
                                    '<input class="form-check-input decisionMenuOption" ' +
                                            'name="decisionMenuOption_' + labelIndex + '_' + articleIndex + '" ' +
                                            'value="1" data-wikigold-label="' + labelIndex + '" ' +
                                            'data-wikigold-article="' + articleIndex + '" type="radio">' +
                                    '</div>' +
                                    '<div class="col-3 text-center">' +
                                    '<input class="form-check-input decisionMenuOption" ' +
                                            'name="decisionMenuOption_' + labelIndex + '_' + articleIndex + '" ' +
                                            'value="2" data-wikigold-label="' + labelIndex + '" ' +
                                            'data-wikigold-article="' + articleIndex + '" type="radio">' +
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
                            const decisions = that.edl[labelIndex];
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
            });
    }
}