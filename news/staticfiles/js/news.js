let currentPage = 1;

function renderPagination(totalPages, currentPage) {
    const prevPageItem = document.getElementById("prev-page-item");
    const nextPageItem = document.getElementById("next-page-item");
    const pageInfo = document.getElementById("page-info");
    
    prevPageItem.classList.toggle("disabled", currentPage === 1);
    nextPageItem.classList.toggle("disabled", currentPage === totalPages);
    pageInfo.innerText = `Page ${currentPage} of ${totalPages}`;
}

function updateAppliedFilters() {
    const filterContainer = document.getElementById("applied-filters");
    filterContainer.innerHTML = ""; // Clear previous filters

    let search = document.getElementById("search-input").value;
    let date = document.getElementById("date-filter").value;
    let sentiment = document.getElementById("sentiment-select").value;

    const filters = [];

    if (search) {
        filters.push({ label: `Search: ${search}`, id: "search-input", type: "search" });
    }
    if (date) {
        filters.push({ label: `Date: ${date}`, id: "date-filter", type: "date" });
    }
    if (sentiment) {
        filters.push({ label: `Sentiment: ${sentiment}`, id: "sentiment-select", type: "sentiment" });
    }

    // Display selected filters below with a cross button (❌) to remove
    filters.forEach(filter => {
        const filterBadge = document.createElement("span");
        filterBadge.className = "badge bg-light text-dark me-2 mb-2 d-inline-flex align-items-center";
        filterBadge.innerHTML = `${filter.label} <button onclick="clearFilter('${filter.id}', '${filter.type}')" class="btn-close btn-close-sm ms-2" aria-label="Remove filter"></button>`;
        filterContainer.appendChild(filterBadge);
    });

    // Ensure filters section remains visible even when no results are found
    filterContainer.style.display = filters.length ? "flex" : "none";
}

function clearFilter(filterId, type) {
    document.getElementById(filterId).value = "";
    fetchNews(); // Refresh results after filter removal
}

function fetchNews(page = 1) {
    if (page < 1) return; // Prevent negative pages

    currentPage = page;
    document.getElementById("page-info").innerText = `Page ${currentPage}`;

    const search = document.getElementById("search-input").value;
    const date = document.getElementById("date-filter").value;
    const sentiment = document.getElementById("sentiment-select").value;

    fetch(`/news/news_get/?search=${search}&date=${date}&sentiment=${sentiment}&page=${page}`)
        .then(response => response.json())
        .then(data => {
            const newsGrid = document.getElementById("news-grid");
            newsGrid.innerHTML = ""; // Clear previous results

            if (data.news.length > 0) {
                data.news.forEach(article => {
                    const card = document.createElement("div");
                    card.className = "col";
                    card.innerHTML = `
                        <div class="card h-100 shadow-sm transition-hover">
                            <div class="card-body">
                                <h3 class="card-title fs-5 fw-bold">${article.title}</h3>
                                <p class="card-text text-dark"><strong>Source:</strong> ${article.source}</p>
                                <p class="card-text text-dark"><strong>Last Updated:</strong> ${article.last_updated}</p>
                                <p class="card-text">
                                    <strong>Sentiment:</strong> 
                                    <span class="${getSentimentClass(article.sentiment)}">${article.sentiment}</span>
                                </p>
                            </div>
                            <div class="card-footer bg-transparent border-top-0">
                                <a href="/news/news_get/${article.article_id}/" class="btn btn-success btn-sm rounded-pill">
                                    Read More
                                </a>
                            </div>
                        </div>
                    `;
                    newsGrid.appendChild(card);
                });
            } else {
                newsGrid.innerHTML = `<div class="col-12 text-center"><p class="text-danger">No news articles found. Try adjusting your filters.</p></div>`;
            }

            updateAppliedFilters();
            updatePaginationControls(data.total_pages);
        })
        .catch(error => console.error("Error fetching news:", error));
}

function updatePaginationControls(totalPages) {
    const prevPageItem = document.getElementById("prev-page-item");
    const nextPageItem = document.getElementById("next-page-item");
    
    prevPageItem.classList.toggle("disabled", currentPage === 1);
    nextPageItem.classList.toggle("disabled", currentPage >= totalPages);
}

function getSentimentClass(sentiment) {
    if (typeof sentiment !== "string") {
        return ""; 
    }

    switch (sentiment.toLowerCase()) {
        case "positive": return "text-success fw-semibold";
        case "neutral": return "text-secondary fw-semibold";
        case "negative": return "text-danger fw-semibold";
        default: return "";
    }
}

// Add CSS for hover effect
document.addEventListener('DOMContentLoaded', function() {
    const style = document.createElement('style');
    style.textContent = `
        .transition-hover {
            transition: transform 0.3s ease;
        }
        .transition-hover:hover {
            transform: translateY(-5px);
        }
    `;
    document.head.appendChild(style);
});

window.onload = () => fetchNews();
