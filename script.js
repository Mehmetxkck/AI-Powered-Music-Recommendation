// Constants
const MOOD_BUTTON_CLASS = '.mood-button';
const RECOMMENDATIONS_CONTAINER_ID = 'recommendations-container';
const BACKEND_URL = 'http://127.0.0.1:5000'; // Consider moving this to a config file

// DOM Elements
const moodButtons = document.querySelectorAll(MOOD_BUTTON_CLASS);
const recommendationsContainer = document.getElementById(RECOMMENDATIONS_CONTAINER_ID);

// Event Listeners
moodButtons.forEach(button => {
    button.addEventListener('click', () => {
        const mood = button.dataset.mood;
        getRecommendations(mood);
    });
});

// Display User Profile Information
async function displayUserData() {
    try {
        const response = await fetch(`${BACKEND_URL}/user_data`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const userData = await response.json();
        const userNameElement = document.getElementById('user-name');
        const userImageElement = document.getElementById('user-image');
        userNameElement.textContent = userData.display_name;
        userImageElement.src = userData.images[0].url;
    } catch (error) {
        console.error('Error fetching user data:', error);
        // Optional: Display a default user image and name if user data fetch fails
        document.getElementById('user-name').textContent = 'Guest';
        document.getElementById('user-image').src = 'default-avatar.png'; // Replace with default avatar image
    }
}

displayUserData();

/**
 * Fetches music recommendations from the backend based on the selected mood.
 * @param {string} mood - The selected mood (e.g., "happy", "sad").
 */
async function getRecommendations(mood) {
    // Display loading indicator
    displayLoadingIndicator();

    try {
        const response = await fetch(`${BACKEND_URL}/recommendations`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ mood: mood })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const recommendations = await response.json();
        displayRecommendations(recommendations);
    } catch (error) {
        displayError(error.message);
    }
}

/**
 * Displays the fetched recommendations in the recommendations container.
 * @param {Array} recommendations - An array of song objects.
 */
function displayRecommendations(recommendations) {
    recommendationsContainer.innerHTML = ''; // Clear previous content

    if (recommendations.length === 0) {
        displayNoRecommendations();
        return;
    }

    recommendations.forEach(song => {
        const recommendationDiv = createRecommendationDiv(song);
        recommendationsContainer.appendChild(recommendationDiv);
    });
}

/**
 * Creates a div element for a single song recommendation.
 * @param {Object} song - The song object.
 * @returns {HTMLDivElement} - The div element for the song.
 */
function createRecommendationDiv(song) {
    const recommendationDiv = document.createElement('div');
    recommendationDiv.classList.add('recommendation');
    recommendationDiv.textContent = `${song.title} - ${song.artist}`;

    // Optional: Add an animation to the new recommendation div
    recommendationDiv.classList.add('fade-in');

    return recommendationDiv;
}

/**
 * Displays a loading indicator in the recommendations container.
 */
function displayLoadingIndicator() {
    recommendationsContainer.innerHTML = '<p>Loading...</p>';
}

/**
 * Displays an error message in the recommendations container.
 * @param {string} message - The error message to display.
 */
function displayError(message) {
    recommendationsContainer.innerHTML = `<p>Error: ${message}</p>`;
}

/**
 * Displays a message when there are no recommendations.
 */
function displayNoRecommendations() {
    recommendationsContainer.innerHTML = '<p>No recommendations found.</p>';
}

/**
 * Optional: Add loading spinner animation when loading recommendations.
 * This can be added to the CSS for better UX.
 */
