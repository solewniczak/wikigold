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
        const algorithmForm = document.querySelector("#algorithm-form");

        if (that.url.searchParams.has('article')) {
            const articleId = that.url.searchParams.get('article');
            that.loadArticleById(articleId)
                .then(result => {
                    searchForm.querySelector("input[name=title]").value = result.title;
                    if (that.url.searchParams.has('algorithm')) {
                        const algorithm = JSON.parse(that.url.searchParams.get('algorithm'));
                        that.runAlgorithm(algorithm);
                    }
                });
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

        algorithmForm.addEventListener("submit", event => {
            event.preventDefault();
            const formData = new FormData(algorithmForm);
            const algorithm = Object.fromEntries(formData);

            that.url.searchParams.set('algorithm', JSON.stringify(algorithm));
            window.history.replaceState('', '', that.url.href);

            that.runAlgorithm(algorithm);
        });

        // modify EDL on user decision
        document.addEventListener("click",event => {
            if (event.target && 'wikigoldLabel' in event.target.dataset) {
                const radio = event.target;
                const labelIndex = radio.dataset.wikigoldLabel;
                that.edl[labelIndex].decision = radio.value;
            }
        });

        const ngramsDisplayCheckboxes = document.querySelectorAll("#ngramsDisplay input");
        ngramsDisplayCheckboxes.forEach(checkbox => {
            checkbox.addEventListener("change", event => {
                const ngram = event.target.value;
                if (event.target.checked) {
                    // show links
                    document.querySelectorAll(".ngram-link-" + ngram).forEach(ngramSpan => {
                        ngramSpan.classList.add("ngram-link");
                    });
                } else {
                    // hide links
                    document.querySelectorAll(".ngram-link-" + ngram).forEach(ngramSpan => {
                        ngramSpan.classList.remove("ngram-link");
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
                span.classList.add("ngram");
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

    runAlgorithm(algorithm) {
        const that = this;
        const article = document.querySelector("article");

        const articleId = that.url.searchParams.get('article');

        if (!articleId) return;

        const requestURL = new URL('/api/candidateLabels/' + articleId, that.baseUrl);
        requestURL.searchParams.append('algorithm', JSON.stringify(algorithm));
        return fetch(requestURL.href, {
            method: 'GET'
        })
            .then(response => response.json())
            .then(result => {
                console.log(result);
                that.edl = result;
                // remove old links
                article.querySelectorAll("span").forEach(span => {
                    if (span.classList.contains("ngram")) {
                        span.className = "ngram";
                    } else {
                        span.className = "";
                    }
                    // remove events
                    span.replaceWith(span.cloneNode(true));
                });
                that.edl.forEach((label, labelIndex) => {
                    const line = article.querySelectorAll("p")[label.line];
                    let span = line.querySelectorAll("span.ngram")[label.start];
                    const showBorder = [span];
                    // collect spans which should be bordered
                    for (let i = 1; i < label.ngrams; i++) {
                        span = span.nextSibling;  // space node
                        showBorder.push(span)
                        span = span.nextSibling; // next token
                        showBorder.push(span)
                    }

                    // select correct level for each span
                    showBorder.forEach(span => {
                        for (let i = 1; i < label.ngrams; i++) {
                            span = span.firstChild;
                        }
                        span.classList.add("ngram-link");
                        span.classList.add("ngram-link-" + label.ngrams);

                        let popoverHtml = '<table class="table table-sm">';
                        label.titles.forEach(article => {
                            popoverHtml += '<tr>' +
                                    '<td class="align-middle">' +
                                    '<label class="col-form-label">' + article.title +'</label>' +
                                    '</td>' +
                                    '<td class="align-middle">' +
                                    '<input type="radio" class="form-check-input" name="correct_'+labelIndex+'" ' +
                                            'value="' + article.article_id + '" ' +
                                            'data-wikigold-label="' + labelIndex + '">' +
                                    '</td>' +
                                '</tr>';
                        });
                        popoverHtml += '<tr>' +
                                    '<td class="align-middle">' +
                                    '<label class="col-form-label"><em>none</em></label>' +
                                    '</td>' +
                                    '<td class="align-middle">' +
                                    '<input type="radio" class="form-check-input decisionMenuOption" ' +
                                            'name="correct_' + labelIndex + '" ' +
                                            'value="" data-wikigold-label="' + labelIndex + '">' +
                                    '</td>' +
                                '</tr>';
                        popoverHtml += '</table>';

                        // create popovers
                        const popover = new bootstrap.Popover(span, {
                            "title": label.name,
                            "html": true,
                            "sanitize": false,
                            "content": popoverHtml,
                            "placement": "bottom",
                            "trigger": "manual",
                            "template": '<div class="popover ngram-popover-' + label.ngrams + '" role="tooltip">' +
                                '<div class="popover-arrow"></div>' +
                                '<h3 class="popover-header"></h3>' +
                                '<div class="popover-body"></div>' +
                                '</div>'
                        });

                        // only one popover at time - stop event propagation
                        span.addEventListener('click', event => {
                            // check if ngram is active
                            if (span.classList.contains('ngram-link')) {
                                event.stopPropagation();
                                popover.toggle();
                            }
                        });
                        // fill the values of form with the EDL
                        span.addEventListener('shown.bs.popover', event => {
                            if ('decision' in label) {
                                const popoverElement = popover.getTipElement();
                                popoverElement.querySelector('input[type=radio][value="'+label.decision+'"]').checked = true;
                            }
                        });

                    });
                });
            });
    }
}