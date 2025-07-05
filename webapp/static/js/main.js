/**
 * Main JavaScript for MemeOS
 */

document.addEventListener("DOMContentLoaded", function () {
  // Theme toggle functionality
  const themeToggleBtn = document.getElementById("theme-toggle");
  const htmlElement = document.documentElement;
  const themeIcon = themeToggleBtn.querySelector("i");

  // Function to update theme icon
  function updateThemeIcon(isDark) {
    if (isDark) {
      themeIcon.classList.remove("fa-sun");
      themeIcon.classList.add("fa-moon");
    } else {
      themeIcon.classList.remove("fa-moon");
      themeIcon.classList.add("fa-sun");
    }
  }

  // Initialize theme based on saved preference or system preference
  const savedTheme = localStorage.getItem("theme");
  if (savedTheme) {
    htmlElement.setAttribute("data-bs-theme", savedTheme);
    updateThemeIcon(savedTheme === "dark");
  } else {
    // Check system preference
    const systemPrefersDark = window.matchMedia(
      "(prefers-color-scheme: dark)"
    ).matches;
    htmlElement.setAttribute(
      "data-bs-theme",
      systemPrefersDark ? "dark" : "light"
    );
    updateThemeIcon(systemPrefersDark);
  }

  // Toggle theme on button click
  themeToggleBtn.addEventListener("click", function () {
    const currentTheme = htmlElement.getAttribute("data-bs-theme");
    const newTheme = currentTheme === "dark" ? "light" : "dark";

    htmlElement.setAttribute("data-bs-theme", newTheme);
    localStorage.setItem("theme", newTheme);
    updateThemeIcon(newTheme === "dark");
  });

  // Handle image preview
  const imageInputs = document.querySelectorAll('input[type="file"]');

  imageInputs.forEach((input) => {
    input.addEventListener("change", function (e) {
      const file = e.target.files[0];

      // Check if file exists and is an image
      if (file && file.type.match("image.*")) {
        // Find closest form container to add preview to
        const formGroup = this.closest(".mb-3");

        // Remove any existing preview
        const existingPreview = formGroup.querySelector(".image-preview");
        if (existingPreview) {
          existingPreview.remove();
        }

        // Create preview image
        const reader = new FileReader();
        reader.onload = function (e) {
          const preview = document.createElement("img");
          preview.src = e.target.result;
          preview.className = "image-preview";
          preview.alt = "Preview";

          formGroup.appendChild(preview);
        };
        reader.readAsDataURL(file);
      }
    });
  });

  // Enhance meme source indicators
  const templateIndicators = document.querySelectorAll(".template-indicator");
  templateIndicators.forEach((indicator) => {
    // Add animation effect
    indicator.style.opacity = "0.85";

    // Add hover effect
    indicator.addEventListener("mouseenter", function () {
      this.style.opacity = "1";
    });

    indicator.addEventListener("mouseleave", function () {
      this.style.opacity = "0.85";
    });

    // Add icon based on source
    if (indicator.classList.contains("from-template")) {
      // Make sure it shows the correct class
      indicator.classList.remove("no-template");
      indicator.classList.add("from-template");

      if (!indicator.querySelector(".fas.fa-check-circle")) {
        const icon = document.createElement("i");
        icon.className = "fas fa-check-circle me-1";
        indicator.prepend(icon);
      }
    } else if (indicator.classList.contains("no-template")) {
      // Make sure it shows the correct class
      indicator.classList.remove("from-template");
      indicator.classList.add("no-template");

      if (!indicator.querySelector(".fas.fa-image")) {
        const icon = document.createElement("i");
        icon.className = "fas fa-image me-1";
        indicator.prepend(icon);
      }
    }
  });

  // Scroll chat to bottom
  const chatContainer = document.getElementById("chatContainer");
  if (chatContainer) {
    chatContainer.scrollTop = chatContainer.scrollHeight;

    // Auto-scroll when new messages appear
    const observer = new MutationObserver(() => {
      chatContainer.scrollTop = chatContainer.scrollHeight;
    });

    observer.observe(chatContainer, {
      childList: true,
      subtree: true,
    });
  }

  // Confirm clear chat
  const clearChatForm = document.querySelector('form[action*="clear-chat"]');
  if (clearChatForm) {
    clearChatForm.addEventListener("submit", function (e) {
      if (!confirm("Are you sure you want to clear the chat history?")) {
        e.preventDefault();
      }
    });
  }

  // Form validation feedback
  const forms = document.querySelectorAll("form");
  forms.forEach((form) => {
    form.addEventListener(
      "submit",
      function (event) {
        if (!form.checkValidity()) {
          event.preventDefault();
          event.stopPropagation();
        }

        form.classList.add("was-validated");
      },
      false
    );
  });

  // Clear form on page load to prevent issues on refresh
  const memeForm = document.querySelector(".meme-form");
  if (memeForm) {
    // Clear form inputs
    memeForm.reset();

    // Clear image preview
    const imagePreview = document.getElementById("imagePreview");
    if (imagePreview) {
      imagePreview.style.display = "none";
      imagePreview.innerHTML = "";
    }

    // Show upload placeholder
    const uploadPlaceholder = document.querySelector(".upload-placeholder");
    if (uploadPlaceholder) {
      uploadPlaceholder.style.display = "block";
    }

    // Remove any existing result sections
    const existingResults = document.querySelectorAll(".result-section");
    existingResults.forEach((result) => {
      if (result.parentElement && result.parentElement.parentElement) {
        result.parentElement.parentElement.remove();
      }
    });
  }

  // File upload handling
  const fileInput = document.getElementById("imageInput");
  const uploadArea = document.getElementById("uploadArea");
  const imagePreview = document.getElementById("imagePreview");
  const uploadPlaceholder = document.querySelector(".upload-placeholder");

  if (fileInput && uploadArea) {
    // Handle file selection
    fileInput.addEventListener("change", function (e) {
      const file = e.target.files[0];
      if (file) {
        displayImagePreview(file);
      }
    });

    // Handle drag and drop
    uploadArea.addEventListener("dragover", function (e) {
      e.preventDefault();
      uploadArea.classList.add("dragover");
    });

    uploadArea.addEventListener("dragleave", function (e) {
      e.preventDefault();
      uploadArea.classList.remove("dragover");
    });

    uploadArea.addEventListener("drop", function (e) {
      e.preventDefault();
      uploadArea.classList.remove("dragover");

      const files = e.dataTransfer.files;
      if (files.length > 0) {
        fileInput.files = files;
        displayImagePreview(files[0]);
      }
    });
  }

  function displayImagePreview(file) {
    const reader = new FileReader();
    reader.onload = function (e) {
      if (imagePreview && uploadPlaceholder) {
        imagePreview.innerHTML = `<img src="${e.target.result}" alt="Preview">`;
        imagePreview.style.display = "block";
        uploadPlaceholder.style.display = "none";
      }
    };
    reader.readAsDataURL(file);
  }

  // Loading spinner functions
  function showLoadingSpinner() {
    const generateBtn = document.getElementById("generateBtn");
    if (generateBtn) {
      generateBtn.innerHTML =
        '<i class="fas fa-spinner fa-spin me-2"></i>Generating...';
      generateBtn.disabled = true;
    }
  }

  function hideLoadingSpinner() {
    const generateBtn = document.getElementById("generateBtn");
    if (generateBtn) {
      generateBtn.innerHTML = '<i class="fas fa-magic me-2"></i>Generate Meme';
      generateBtn.disabled = false;
    }
  }

  // Enhance meme result cards
  const memeResultDiv = document.getElementById("meme-result");
  if (memeResultDiv) {
    const memeImg = memeResultDiv.querySelector("img");
    if (memeImg) {
      // Add click to enlarge functionality
      memeImg.style.cursor = "pointer";
      memeImg.addEventListener("click", function () {
        const modal = document.createElement("div");
        modal.className =
          "position-fixed top-0 start-0 w-100 h-100 d-flex justify-content-center align-items-center";
        modal.style.backgroundColor = "rgba(0,0,0,0.85)";
        modal.style.zIndex = "9999";

        const modalImg = document.createElement("img");
        modalImg.src = this.src;
        modalImg.className = "img-fluid";
        modalImg.style.maxHeight = "90vh";
        modalImg.style.maxWidth = "90vw";
        modalImg.style.objectFit = "contain";
        modalImg.style.boxShadow = "0 0 20px rgba(0,0,0,0.5)";

        modal.appendChild(modalImg);
        document.body.appendChild(modal);

        // Close on click
        modal.addEventListener("click", function () {
          this.remove();
        });
      });
    }
  }

  // Add submit handler to meme generation form
  if (memeForm) {
    memeForm.addEventListener("submit", function (e) {
      e.preventDefault(); // Prevent default form submission

      // Check if an image file is selected
      const imageInput = document.getElementById("imageInput");
      if (!imageInput || !imageInput.files || imageInput.files.length === 0) {
        showErrorMessage(
          "Please select an image file before generating a meme!"
        );
        return;
      }

      // Check if at least one text field has content
      const topText = document
        .querySelector('input[name="top_text"]')
        .value.trim();
      const bottomText = document
        .querySelector('input[name="bottom_text"]')
        .value.trim();
      const additionalText = document
        .querySelector('textarea[name="additional_text"]')
        .value.trim();

      if (!topText && !bottomText && !additionalText) {
        showErrorMessage("Please enter some text for your meme!");
        return;
      }

      // Show loading spinner
      showLoadingSpinner();

      // Create FormData object
      const formData = new FormData(this);

      // Combine text fields into a single caption
      const caption_parts = [];
      if (topText) caption_parts.push(topText);
      if (bottomText) caption_parts.push(bottomText);
      if (additionalText) caption_parts.push(additionalText);

      const caption = caption_parts.join("|");

      // Set the combined caption
      formData.set("caption", caption);

      // Remove individual text fields to avoid confusion
      formData.delete("top_text");
      formData.delete("bottom_text");
      formData.delete("additional_text");

      console.log("Sending caption:", caption); // Debug log

      // Send POST request to API
      fetch(this.action, {
        method: "POST",
        body: formData,
        headers: {
          "X-Requested-With": "XMLHttpRequest",
        },
      })
        .then((response) => {
          if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
          }

          // Check if response is JSON or file
          const contentType = response.headers.get("content-type");
          if (contentType && contentType.includes("application/json")) {
            return response.json();
          } else {
            // Handle file response
            return response.blob().then((blob) => {
              const url = URL.createObjectURL(blob);
              return { meme_url: url, is_file: true };
            });
          }
        })
        .then((data) => {
          if (data.error) {
            throw new Error(data.error);
          }

          // Hide loading spinner
          hideLoadingSpinner();

          // Display the generated meme
          displayGeneratedMeme(
            data.meme_url,
            data.from_template,
            data.similarity_score
          );

          // Show success message
          showSuccessMessage("Meme generated successfully!");
        })
        .catch((error) => {
          console.error("Error:", error);
          hideLoadingSpinner();
          showErrorMessage(`Error generating meme: ${error.message}`);
        });
    });
  }
});

// Function to clear previously generated meme
function clearPreviousMeme() {
  // Check if we're on a new page load (not form submission)
  if (document.referrer !== document.location.href) {
    // Hide the meme section if it exists
    const memeSection = document.querySelector('.card:has(img[src^="/data/"])');
    if (memeSection) {
      memeSection.style.display = "none";
    }
  }
}

// Helper function to display generated meme
function displayGeneratedMeme(memeUrl, fromTemplate, similarityScore) {
  // Remove existing result section if any
  const existingResult = document.querySelector(".result-section");
  if (existingResult) {
    existingResult.remove();
  }

  // Create new result section
  const resultSection = document.createElement("div");
  resultSection.className = "row mt-5";
  resultSection.innerHTML = `
    <div class="col-12">
      <div class="result-section">
        <div class="result-header">
          <h2>
            <i class="fas fa-check-circle me-2"></i>Meme Generated Successfully!
          </h2>
          <div class="template-info">
            ${
              fromTemplate
                ? `<i class="fas fa-template me-1"></i>Generated from template (${
                    similarityScore ? similarityScore.toFixed(1) : 0
                  }% match)`
                : `<i class="fas fa-sparkles me-1"></i>Original creation`
            }
          </div>
        </div>
        <div class="result-body">
          <div class="meme-display">
            <img src="${memeUrl}" alt="Generated Meme" class="generated-meme" />
          </div>
          <div class="result-actions">
            <a href="${memeUrl}" class="btn btn-primary" target="_blank">
              <i class="fas fa-external-link-alt me-1"></i> View Full Size
            </a>
            <a href="${memeUrl}" class="btn btn-success" download="meme.jpg">
              <i class="fas fa-download me-1"></i> Download
            </a>
            <button class="btn btn-secondary" onclick="shareOnTwitter()">
              <i class="fab fa-twitter me-1"></i> Share
            </button>
            <button class="btn btn-outline-primary" onclick="generateAnother()">
              <i class="fas fa-redo me-1"></i> Generate Another
            </button>
          </div>
        </div>
      </div>
    </div>
  `;

  // Add to the container
  const container = document.querySelector(".generator-section .container");
  if (container) {
    container.appendChild(resultSection);

    // Scroll to the result
    resultSection.scrollIntoView({ behavior: "smooth" });
  }
}

// Helper function to show success message
function showSuccessMessage(message) {
  const alertDiv = document.createElement("div");
  alertDiv.className = "alert alert-success alert-dismissible fade show";
  alertDiv.innerHTML = `
    ${message}
    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
  `;

  // Insert at the top of the form
  const form = document.querySelector(".meme-form");
  if (form) {
    form.insertBefore(alertDiv, form.firstChild);

    // Auto-dismiss after 5 seconds
    setTimeout(() => {
      if (alertDiv.parentNode) {
        alertDiv.remove();
      }
    }, 5000);
  }
}

// Helper function to show error message
function showErrorMessage(message) {
  const alertDiv = document.createElement("div");
  alertDiv.className = "alert alert-danger alert-dismissible fade show";
  alertDiv.innerHTML = `
    ${message}
    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
  `;

  // Insert at the top of the form
  const form = document.querySelector(".meme-form");
  if (form) {
    form.insertBefore(alertDiv, form.firstChild);

    // Auto-dismiss after 10 seconds
    setTimeout(() => {
      if (alertDiv.parentNode) {
        alertDiv.remove();
      }
    }, 10000);
  }
}

// Helper function to download meme
function downloadMeme(url) {
  const a = document.createElement("a");
  a.href = url;
  a.download = "generated_meme.png";
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}

// Helper function to share meme (placeholder)
function shareMeme(url) {
  if (navigator.share) {
    navigator.share({
      title: "Check out my meme!",
      url: url,
    });
  } else {
    // Fallback: copy URL to clipboard
    navigator.clipboard.writeText(url).then(() => {
      showSuccessMessage("Meme URL copied to clipboard!");
    });
  }
}

// Global helper functions for template actions
window.shareOnTwitter = function () {
  const memeImg = document.querySelector(".generated-meme");
  if (memeImg) {
    const tweetText = encodeURIComponent(
      "Check out this awesome meme I created with MemeOS! 🔥"
    );
    const tweetUrl = `https://twitter.com/intent/tweet?text=${tweetText}`;
    window.open(tweetUrl, "_blank");
  }
};

window.generateAnother = function () {
  // Clear the form
  const form = document.querySelector(".meme-form");
  if (form) {
    form.reset();

    // Clear image preview
    const imagePreview = document.getElementById("imagePreview");
    if (imagePreview) {
      imagePreview.style.display = "none";
      imagePreview.innerHTML = "";
    }

    // Show upload placeholder
    const uploadPlaceholder = document.querySelector(".upload-placeholder");
    if (uploadPlaceholder) {
      uploadPlaceholder.style.display = "block";
    }

    // Remove result section
    const resultSection = document.querySelector(".result-section");
    if (resultSection) {
      resultSection.parentElement.parentElement.remove();
    }

    // Scroll back to top
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
};
