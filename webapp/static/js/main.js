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
    // Show any existing result section
    const existingResult = document.querySelector(".result-section");
    if (existingResult) {
      existingResult.closest(".row").style.display = "block";
      existingResult.style.display = "block";
    }

    memeForm.addEventListener("submit", function (e) {
      // Show loading state
      showLoadingSpinner();

      // Let the form submit normally
      // The server will handle the response and render the result section
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
      generateBtn.innerHTML = "Generate Meme";
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

  // Function to clear template
  function clearTemplate() {
    // Clear template preview
    const templatePreview = document.getElementById("templatePreview");
    if (templatePreview) {
      templatePreview.style.display = "none";
    }

    // Show upload placeholder
    const uploadPlaceholder = document.querySelector(".upload-placeholder");
    if (uploadPlaceholder) {
      uploadPlaceholder.style.display = "block";
    }

    // Clear session storage
    sessionStorage.removeItem("selectedTemplate");

    // Redirect to clean URL
    window.location.href = window.location.pathname;
  }

  // Function to generate another meme
  function generateAnother() {
    // Clear form
    const form = document.querySelector(".meme-form");
    if (form) {
      form.reset();
    }

    // Clear template
    clearTemplate();

    // Hide result section
    const resultSection = document.querySelector(".result-section");
    if (resultSection) {
      resultSection.closest(".row").style.display = "none";
    }

    // Scroll to top
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  // Function to share on Twitter
  function shareOnTwitter() {
    const memeImg = document.querySelector(".generated-meme");
    if (memeImg) {
      const memeUrl = memeImg.getAttribute("data-view-url") || memeImg.src;
      const tweetText = encodeURIComponent(
        "Check out this awesome meme I created with MemeOS! 🔥"
      );
      const tweetUrl = `https://twitter.com/intent/tweet?text=${tweetText}&url=${encodeURIComponent(
        memeUrl
      )}`;
      window.open(tweetUrl, "_blank");
    }
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
  // Clean up the meme URL to work with serve_data_file route
  const cleanMemeUrl = memeUrl.replace("/data/", "/");

  // Get the proper URL using Flask's url_for (via data attribute)
  const urlTemplate = document.querySelector('meta[name="meme-url-template"]');
  const baseUrl = urlTemplate ? urlTemplate.getAttribute("content") : "/data";
  const properMemeUrl = `${baseUrl}/${cleanMemeUrl.replace(/^\//, "")}`;

  // Check if we already have a server-rendered result section
  const existingResult = document.querySelector(".result-section");
  if (existingResult) {
    // Update the existing result section
    const memeImage = existingResult.querySelector(".generated-meme");
    if (memeImage) {
      memeImage.src = properMemeUrl;
      memeImage.setAttribute("data-view-url", properMemeUrl);
      memeImage.setAttribute("data-download-url", properMemeUrl);
    }

    // Update view and download links
    const viewLink = existingResult.querySelector("a.btn-primary");
    const downloadLink = existingResult.querySelector("a.btn-success");
    if (viewLink) viewLink.href = properMemeUrl;
    if (downloadLink) downloadLink.href = properMemeUrl;

    // Update template info if needed
    const templateInfo = existingResult.querySelector(".template-info");
    if (templateInfo) {
      templateInfo.innerHTML = fromTemplate
        ? `<i class="fas fa-template me-1"></i>Generated from template (${
            similarityScore ? similarityScore.toFixed(1) : 0
          }% match)`
        : `<i class="fas fa-sparkles me-1"></i>Original creation`;
    }

    // Make sure it's visible
    existingResult.closest(".row").style.display = "block";
    existingResult.style.display = "block";

    // Scroll to the result
    existingResult.scrollIntoView({ behavior: "smooth" });
    return;
  }

  // If no existing result section, create a new one
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
            <img src="${properMemeUrl}" alt="Generated Meme" class="generated-meme" 
                 data-view-url="${properMemeUrl}" 
                 data-download-url="${properMemeUrl}" />
          </div>
          <div class="result-actions">
            <a href="${properMemeUrl}" class="btn btn-primary" target="_blank">
              <i class="fas fa-external-link-alt me-1"></i> View Full Size
            </a>
            <a href="${properMemeUrl}" class="btn btn-success" download="meme.jpg">
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
