class App {
    constructor(prefix, maxNgrams) {
        this.prefix = prefix;
        this.maxNgrams = maxNgrams;
        this.url =  new URL(document.location);
    }

    requestUrl(path, params) {
        if (params) {
            const searchParams = new URLSearchParams(params);
            return this.prefix + path + '?' + searchParams
        } else {
            return this.prefix + path
        }
    }

    escapeAttribute(value) {
        // https://stackoverflow.com/questions/9187946/escaping-inside-html-tag-attribute-value
        return value
            .replace(/&/g, "&amp;")
            .replace(/"/g, "&quot;");
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
            that.lockForms();
            that.loadArticleById(articleId)
                .then(result => {
                    searchForm.querySelector("input[name=title]").value = result.title;
                    if (that.url.searchParams.has('algorithm')) {
                        const algorithm = JSON.parse(that.url.searchParams.get('algorithm'));
                        return that.runAlgorithm(algorithm);
                    }
                }).then(that.unlockForms);
        }

        searchForm.addEventListener("submit", event => {
            event.preventDefault();
            const formData = new FormData(searchForm);
            const title = formData.get('title');
            const article_source = formData.get('article_source');
            that.lockForms();
            that.loadArticleByTitle(title, article_source)
                .then(result => {
                    that.url.searchParams.set('article', result.id);
                    that.url.searchParams.delete('algorithm');
                    window.history.replaceState('', '', that.url.href);
                }).then(that.unlockForms);
        });

        algorithmForm.addEventListener("submit", event => {
            event.preventDefault();
            const formData = new FormData(algorithmForm);
            const algorithm = Object.fromEntries(formData);

            that.lockForms();
            that.runAlgorithm(algorithm)
                .then(result => {
                    that.url.searchParams.set('algorithm', result.algorithm_key);
                    window.history.replaceState('', '', that.url.href);
                })
                .then(that.applyNgramsDisplaySettings)
                .then(that.unlockForms);
        });

        // modify EDL on user decision
        document.addEventListener("click",event => {
            if (event.target && 'wikigoldLabel' in event.target.dataset) {
                const checkbox = event.target;
                const labelIndex = Number(checkbox.dataset.wikigoldLabel);
                const label = that.edl[labelIndex];

                let checkbox_value = checkbox.value;
                if (!checkbox.checked) {
                    checkbox_value = -1;
                } else if (checkbox.value === '') {
                    checkbox_value = null;
                }

                // uncheck previous decisions
                document.querySelectorAll('input[name=' + checkbox.name + ']').forEach(checkboxInGroup => {
                    if (checkbox !== checkboxInGroup) {
                        checkboxInGroup.checked = false;
                    }
                });

                // lock and unlock tabs for overlapping links
                const popoverElement = checkbox.closest('.popover');
                if (checkbox_value === -1) {
                    popoverElement.querySelectorAll('.nav-link').forEach(navLink => {
                        navLink.classList.remove('disabled');
                    });
                } else {
                    popoverElement.querySelectorAll('.nav-link:not(.active)').forEach(navLink => {
                        navLink.classList.add('disabled');
                    });
                }

                // update decision locally
                that.removeLabelClass(labelIndex, 'ngram-link-resolved');
                that.removeLabelClass(labelIndex, 'ngram-link-none');
                that.removeClassFromOverlappingLabels(labelIndex, 'ngram-link-covered');
                if (checkbox_value === -1) {
                    delete label.decision;
                } else {
                    label.decision = checkbox_value;
                    that.addLabelClass(labelIndex, 'ngram-link-resolved');
                    if (checkbox_value === null) {
                        that.addLabelClass(labelIndex, 'ngram-link-none');
                    }
                    that.addClassToOverlappingLabels(labelIndex, 'ngram-link-covered');
                }

                // send decision to server
                const article = that.url.searchParams.get('article');
                const line_nr = label.line;
                const start = label.start;
                const length = label.ngrams;
                const algorithm = that.url.searchParams.get('algorithm');

                const requestUrl = that.requestUrl('/api/decision');
                const data = {  article: article,
                                algorithm: algorithm,
                                source_article_id: article,
                                source_line_nr: line_nr,
                                start: start,
                                length: length,
                                destination_article_id: checkbox_value}
                return fetch(requestUrl, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(data),
                })
                    .then(response => response.json())
                    .then(result => {
                        console.log(result);
                    });
            }
        });

        const ngramsDisplayCheckboxes = document.querySelectorAll("#ngramsDisplay input");
        ngramsDisplayCheckboxes.forEach(checkbox => {
            checkbox.addEventListener("change", that.applyNgramsDisplaySettings);
        });

        // key shortcuts for ngrams display
        document.addEventListener('keydown', event => {
            if (event.target.tagName === 'INPUT' ) {
                return;
            }
            for (let i = 0; i < that.maxNgrams; i++) {
                if (event.code === "Digit" + (i+1)) {
                    ngramsDisplayCheckboxes[i].checked ^= 1;
                    that.applyNgramsDisplaySettings();
                    return;
                }
            }

        });

        // tooltips for Wikipedia's articles
        new bootstrap.Tooltip(document.body, {
            selector: '[data-bs-toggle="tooltip"]',
            html: true
        });

        // hide popovers when users clicks not in popover itself
        document.addEventListener('click', event => {
            if (event.target && event.target.closest('.popover') === null &&
                // fixes strange behaviour of DataTable - .pagination is not child of .popover
                event.target.closest('.pagination') === null) {
                if (that.previousPopover) {
                    that.previousPopover.hide();
                }
            }
        });
    }

    lockForms() {
        const formElements = document.querySelectorAll("input, select, textarea, button");
        formElements.forEach(formElement => {
            formElement.disabled = true;
        });
    }

    unlockForms() {
        const formElements = document.querySelectorAll("input, select, textarea, button");
        formElements.forEach(formElement => {
            formElement.disabled = false;
        });
    }

    applyNgramsDisplaySettings() {
        const ngramsDisplayCheckboxes = document.querySelectorAll("#ngramsDisplay input");
        ngramsDisplayCheckboxes.forEach(checkbox => {
            const ngram = checkbox.value;
            if (checkbox.checked) {
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
    }

    processLabelSpans(labelIndex, callback) {
        const that = this;
        const label_ngrams = that.labels_ngrams[labelIndex];
        label_ngrams.ngrams.forEach((ngramIndex, index) => {
            const article = document.querySelector("article");
            const line = article.querySelectorAll("p")[label_ngrams.line];
            const ngram = line.querySelectorAll("span.ngram")[ngramIndex];

            // select correct span level
            let span = ngram;
            for (let i = 0; i < label_ngrams.ngrams.length; i++) {
                span = span.firstChild;
            }
            callback(span);

            // if we are not processing the last element of the label, add class to a space span between ngrams
            if (index < label_ngrams.ngrams.length-1) {
                let spaceSpan = ngram.nextSibling;
                for (let i = 0; i < label_ngrams.ngrams.length; i++) {
                    spaceSpan = spaceSpan.firstChild;
                }
                callback(spaceSpan);
            }
        });
    }

    getLabelSpans(labelIndex) {
        const that = this;
        const labelSpans = [];
        that.processLabelSpans(labelIndex, span => {
            labelSpans.push(span);
        });
        return labelSpans;
    }

    addLabelClass(labelIndex, className) {
        const that = this;
        that.processLabelSpans(labelIndex, span => {
            span.classList.add(className);
        });
    }

    removeLabelClass(labelIndex, className) {
        const that = this;
        this.processLabelSpans(labelIndex, span => {
            span.classList.remove(className);
        });
    }

    processOverlappingLabels(labelIndex, callback) {
        const that = this;
        const label_ngrams = that.labels_ngrams[labelIndex];
        label_ngrams.ngrams.forEach(ngramIndex => {
            // collect overlapping links
            const labelIndexes = that.ngrams_labels[label_ngrams.line][ngramIndex];
            labelIndexes.forEach(callback);
        });
    }

    addClassToOverlappingLabels(labelIndex, className) {
        const that = this;
        const labelSpans = that.getLabelSpans(labelIndex);
        that.processOverlappingLabels(labelIndex, overlappingLabelIndex => {
            if (labelIndex !== overlappingLabelIndex) {
                    that.processLabelSpans(overlappingLabelIndex, span => {
                        if (!labelSpans.includes(span)) {
                            span.classList.add(className);
                        }
                    });
                }
        });
    }

    removeClassFromOverlappingLabels(labelIndex, className) {
        const that = this;
        that.processOverlappingLabels(labelIndex, overlappingLabelIndex => {
            if (labelIndex !== overlappingLabelIndex) {
                that.removeLabelClass(overlappingLabelIndex, className);
            }
        });
    }

    loadArticleByTitle(title, article_source) {
        const that = this;

        const requestUrl = that.requestUrl('/api/article', {'title': title, 'article_source': article_source})
        return fetch(requestUrl, {
            method: 'GET'
        })
            .then(response => response.json())
            .then(result => that.loadArticleFromResult(result));
    }

    loadArticleById(articleId) {
        const that = this;

        const requestUrl = that.requestUrl('/api/article/' + articleId);
        return fetch(requestUrl, {
            method: 'GET'
        })
            .then(response => response.json())
            .then(result => that.loadArticleFromResult(result));
    }

    loadArticleFromResult(result) {
        const that = this;
        const article = document.querySelector("article");
        that.article = result;

        article.replaceChildren(); // remove old paragraphs
        result.lines.forEach(line => {
            const p = document.createElement("p");
            const content = line.content;
            const tokens = line.tokens;
            const char_spans = [];

            for (let char of content) {
                const charSpan = document.createElement("span");
                charSpan.className = "char";
                charSpan.textContent = char;
                char_spans.push(charSpan);
                if (char === ' ') {
                    let span = document.createElement("span");
                    span.classList.add("space");
                    p.append(span);
                    for (let i = 0; i < that.maxNgrams; i++) {
                        let nextSpan = document.createElement("span");
                        span.append(nextSpan);
                        span = nextSpan;
                    }
                    span.append(charSpan);
                } else {
                    p.append(charSpan);
                }

            }

            for (let token of tokens) {
                const token_start = token[0];
                const token_end = token[1];
                let span = document.createElement("span");
                span.classList.add("ngram");
                char_spans[token_start].before(span);

                for (let i = 0; i < that.maxNgrams; i++) {
                    let nextSpan = document.createElement("span");
                    span.append(nextSpan);
                    span = nextSpan;
                }

                for (let i = token_start; i < token_end; i++) {
                    span.append(char_spans[i]);
                }
            }
            article.append(p);
        });

        //apply wikipedia decisions
        result.wikipedia_decisions.forEach(decision => {
            const line = article.querySelectorAll("p")[decision.line];
            const char_spans = line.querySelectorAll("span.char");

            for (let i = decision.start; i < decision.start+decision.length; i++) {
                let span = char_spans[i];
                let tooltip = '';
                if (decision.destination_article_id == null) {
                    tooltip += '<p>Links to: '+decision.destination_title+'</p>';
                    span.classList.add('wikipedia-link-red');
                } else {
                    span.classList.add('wikipedia-link-blue');
                    if (decision.destination_caption) {
                        tooltip += '<p>Links to: '+decision.destination_title+'</p>';
                        tooltip += '<p>' + decision.destination_caption + '</p>';
                    } else {
                        tooltip += '<p><i>no caption</i></p>';
                    }
                }
                span.title = tooltip;
                span.dataset.bsToggle = "tooltip";
            }
        });
        return result;
    }

    runAlgorithm(algorithm) {
        const that = this;
        const article = document.querySelector("article");

        const articleId = that.url.searchParams.get('article');
        // const paragraphs = parseInt(document.querySelector("input[name=paragraphs]").value);

        if (!articleId) return;

        const requestUrl = that.requestUrl('/api/candidateLabels/' + articleId,
            {'algorithm': JSON.stringify(algorithm)});
        return fetch(requestUrl, {
            method: 'GET'
        })
            .then(response => response.json())
            .then(result => {
                that.edl = result.edl;
                that.ngrams_labels = {};
                that.labels_ngrams = {};
                that.edl.forEach((label, labelIndex) => {
                    that.labels_ngrams[labelIndex] = {line: label.line, ngrams: []};
                    for (let i = label.start; i < label.start+label.ngrams; i++) {
                        that.labels_ngrams[labelIndex].ngrams.push(i);
                    }

                    if (!(label.line in that.ngrams_labels)) {
                        that.ngrams_labels[label.line] = {};
                    }
                    for (let i = label.start; i < label.start+label.ngrams; i++) {
                        if (!(i in that.ngrams_labels[label.line])) {
                        that.ngrams_labels[label.line][i] = [];
                        }
                        that.ngrams_labels[label.line][i].push(labelIndex);
                    }
                });

                // remove old link classes
                const linkNgrams = article.querySelectorAll("span:not(.ngram):not(.space):not(.char)")
                linkNgrams.forEach(span => {
                    span.className = "";
                    delete span.dataset.labels;
                });
                // remove events
                linkNgrams.forEach(span => {
                     span.replaceWith(span.cloneNode(true));
                });

                that.edl.forEach((label, labelIndex) => {
                    const line = article.querySelectorAll("p")[label.line];
                    let span = line.querySelectorAll("span.ngram")[label.start];
                    const showBorder = [span];
                    // collect spans which should be bordered
                    for (let i = 1; i < label.ngrams; i++) {
                        span = span.nextSibling;
                        // sometimes tokens aren't separated by space
                        // sometimes there are more than one space between tokens
                        while (span.classList.contains("space")) {
                            showBorder.push(span)
                            span = span.nextSibling; // next token
                        }
                        showBorder.push(span)
                    }

                    // select correct level for each span
                    showBorder.forEach(span => {
                        for (let i = 0; i < label.ngrams; i++) {
                            span = span.firstChild;
                        }
                        span.classList.add("ngram-link");
                        span.classList.add("ngram-link-" + label.ngrams);

                        const spanLabels = [labelIndex];
                        if ('labels' in span.dataset) {
                            spanLabels.push(...JSON.parse(span.dataset.labels));
                        }
                        span.dataset.labels = JSON.stringify(spanLabels);

                        if ('decision' in label) {
                            span.classList.add("ngram-link-resolved");
                            if (label.decision === null) {
                                span.classList.add("ngram-link-none");
                            }
                            that.addClassToOverlappingLabels(labelIndex, 'ngram-link-covered');
                        }
                    });
                });

                article.querySelectorAll('.ngram-link').forEach(span => {
                    const spanLabels = JSON.parse(span.dataset.labels);

                    let title = '<nav><div class="nav nav-tabs" id="nav-tab" role="tablist" style="padding: .5rem 1rem 0;">';
                    spanLabels.forEach((labelIndex, index) => {
                       const label = that.edl[labelIndex];
                       title += '<button class="nav-link" data-bs-toggle="tab" data-bs-target="#label' + labelIndex + '" ' +
                           'type="button" role="tab">' +
                           '<span class="ngram-tab ngram-tab-' + label.ngrams + '">' + label.name + '</span> (' + label.counter + ')' +
                           '</button>';
                    });
                    title += '</div></nav>';

                    let popoverHtml = '<div style="min-width: 576px;" class="tab-content" id="nav-tabContent">';
                    spanLabels.forEach((labelIndex, index) => {
                        const label = that.edl[labelIndex];
                        popoverHtml += '<div class="tab-pane fade" id="label' + labelIndex + '" role="tabpanel">' +
                        '<table class="table table-sm">' +
                        '<thead><tr><th>Title</th>' +
                        '<th title="<p>Article Counter</p><p>Number of Wikipedia links that points to this article.</p>" data-bs-toggle="tooltip">A</th>' +
                        '<th title="<p>Lable-Article Counter</p><p>Number of Wikipedia links <b>with that label</b> that points to this article.</p>" data-bs-toggle="tooltip">L-A</th>' +
                        '<th></th></tr></thead>' +
                        '<tbody>';
                        label.titles.forEach(article => {
                            let tooltip = '';
                            if (article.redirect_to_title) {
                                tooltip += '<p>Redirects to: ' + article.redirect_to_title + '</p>';
                            }
                            if (article.caption) {
                                tooltip += '<p>' + article.caption + '</p>';
                            } else {
                                tooltip += '<p><i>no caption</i></p>';
                            }

                            popoverHtml += '<tr>' +
                                '<td class="align-middle"><label class="col-form-label">' +
                                '<a href="https://' + that.article.lang + '.wikipedia.org/wiki/' + article.title + '" target="_blank" ' +
                                'data-bs-toggle="tooltip" data-bs-placement="left" title="' + that.escapeAttribute(tooltip) + '">' +
                                article.title +
                                '</a>' +
                                '</label></td>' +
                                '<td>' + article.article_counter + '</td>' +
                                '<td>' + article.label_title_counter + '</td>' +
                                '<td class="align-middle">' +
                                '<input type="checkbox" class="form-check-input" name="correct_' + labelIndex + '" ' +
                                'value="' + article.article_id + '" ' +
                                'data-wikigold-label="' + labelIndex + '">' +
                                '</td>' +
                                '</tr>';
                        });
                        popoverHtml += '</tbody>' +
                            '<tfoot><tr>' +
                            '<td class="align-middle">' +
                            '<label class="col-form-label"><em>none</em></label>' +
                            '</td>' +
                            '<td></td><td></td>' +
                            '<td class="align-middle">' +
                            '<input type="checkbox" class="form-check-input decisionMenuOption" ' +
                            'name="correct_' + labelIndex + '" ' +
                            'value="" data-wikigold-label="' + labelIndex + '">' +
                            '</td>' +
                            '</tr>';
                        popoverHtml += '</tfoot></table></div>';
                    });
                    popoverHtml += '</div>';

                    // create popovers
                    const popover = new bootstrap.Popover(span, {
                        "title": title,
                        "html": true,
                        "sanitize": false,
                        "content": popoverHtml,
                        "contanier": "body",
                        "placement": "bottom",
                        "trigger": "manual",
                        // data-labels allow checkbox event handle the tabs enabling/disabling correctly
                        "template": '<div class="popover" role="tooltip" data-labels="' + span.dataset.labels + '">' +
                            '<div class="popover-arrow"></div>' +
                            '<div class="popover-header" style="padding:0; border-bottom:0;"></div>' +
                            '<div class="popover-body"></div>' +
                            '</div>'
                    });


                    // only one popover at time - stop event propagation
                    span.onclick = event => {
                        // check if ngram is active
                        if (span.classList.contains('ngram-link') && !span.classList.contains('ngram-link-covered')) {
                            event.stopPropagation();
                            if (that.previousPopover !== popover) {
                                if (that.previousPopover) {
                                    that.previousPopover.hide();
                                }
                                popover.show();
                                that.previousPopover = popover;
                            // cold start - when that.previousPopover isn't filled already
                            } else if (popover.getTipElement().offsetParent === null) {
                                popover.show();
                            }
                        }
                    }

                    span.addEventListener('inserted.bs.popover', event => {
                        const popoverElement = popover.getTipElement();
                        //apply to only visible popovers
                        if (popoverElement.offsetParent === null) {
                            return;
                        }
                        // fill with the values of form with the EDL
                        spanLabels.forEach(labelIndex => {
                            const label = that.edl[labelIndex];
                            const labelDivId = '#label' + labelIndex;
                            const labelDiv = popoverElement.querySelector(labelDivId);
                            if ('decision' in label) {
                                let value = label.decision;
                                if (value === null) {
                                    value = ''
                                }
                                labelDiv.querySelector('input[type=checkbox][value="' + value + '"]').checked = true;
                                labelDiv.classList.add('active', 'show');
                                popoverElement.querySelector('.nav-link[data-bs-target="' + labelDivId + '"]')
                                    .classList.add('active');
                                popoverElement.querySelectorAll('.nav-link:not(.active)').forEach(navLink => {
                                    navLink.classList.add('disabled');
                                });
                            }
                        });
                        // activate first tab if there is no decision
                        if (popoverElement.querySelector('.nav-link.active') === null) {
                            popoverElement.querySelector('.nav-link:first-child').classList.add('active');
                            popoverElement.querySelector('.tab-pane:first-child').classList.add('active', 'show');
                        }

                        // creating DataTable must go after selecting input value
                        jQuery(popoverElement).find("table").DataTable({
                            columnDefs: [
                                {orderable: false, targets: 3},
                                {orderSequence: ["desc", "asc"], targets: [1, 2]}
                            ]
                        });
                    });
                });
                return result;
            });
    }
}


class AdminRedis extends App {
    constructor(baseUrl, maxNgrams) {
        super(baseUrl, maxNgrams);
        const that = this;

        const dumpTbodys = document.querySelectorAll('tbody[data-dump-id]');
        dumpTbodys.forEach(dumpTbody => {
            const dumpId = dumpTbody.dataset.dumpId;
            const cacheLabelsButton = dumpTbody.querySelector('.btn-cache-labels');
            const totalLabels = parseInt(dumpTbody.querySelector('.total-labels').textContent);
            const cachedLabelsSpan = dumpTbody.querySelector('span.cached-labels');
            const progressBarTr = dumpTbody.querySelector('tr.progress-bar-row')

            cacheLabelsButton.addEventListener("click", event => {
                progressBarTr.style.display = "table-row";
                const checkProgress = setInterval(() => {
                    const requestUrl = that.requestUrl('/admin/redis/countCachedLabels/' + dumpId);
                    fetch(requestUrl, {
                        method: 'GET'
                    })
                    .then(response => response.json())
                    .then(result => {
                        const progress = (result.cached_labels/totalLabels) * 100;
                        progressBarTr.querySelector('.progress-bar').style.width = progress + "%";
                        cachedLabelsSpan.textContent = result.cached_labels;
                    });
                }, 1000);

                const requestUrl = that.requestUrl('/admin/redis/cacheLabels/' + dumpId);
                fetch(requestUrl, {
                    method: 'GET'
                })
                    .then(response => response.json())
                    .then(result => {
                        progressBarTr.style.display = "none";
                        clearInterval(checkProgress);
                        cachedLabelsSpan.textContent = result.cached_labels;
                });
            });
        });
    }
}