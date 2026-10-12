/**
 * 5-Step Listing Creation & Editing Wizard
 * Manages step navigation, draft persistence (localStorage),
 * Cloudinary image uploads, reordering, and submission.
 */

import { uploadPhotoToCloudinary } from './upload.js';

const DRAFT_KEY = 'nestfinder_listing_draft';

class ListingWizard {
  constructor() {
    this.currentStep = 1;
    this.totalSteps = 5;
    this.photos = [];
    this.isEditMode = window.WIZARD_CONFIG?.isEditMode || false;
    this.listingId = window.WIZARD_CONFIG?.listingId || null;

    this.initElements();
    this.initListeners();

    if (this.isEditMode && window.INITIAL_LISTING_DATA) {
      this.populateData(window.INITIAL_LISTING_DATA);
    } else {
      this.restoreDraft();
    }

    this.updateStepUI();
  }

  initElements() {
    this.stepContainers = document.querySelectorAll('.wizard-step');
    this.progressBar = document.getElementById('wizard-progress-bar');
    this.stepIndicator = document.getElementById('wizard-step-indicator');
    this.prevBtn = document.getElementById('wizard-prev-btn');
    this.nextBtn = document.getElementById('wizard-next-btn');
    this.submitBtn = document.getElementById('wizard-submit-btn');

    this.photoInput = document.getElementById('photo-file-input');
    this.photosGrid = document.getElementById('photos-preview-grid');
    this.uploadProgress = document.getElementById('upload-progress-container');
    this.uploadProgressBar = document.getElementById('upload-progress-bar');
  }

  initListeners() {
    this.prevBtn?.addEventListener('click', () => this.goToPrevStep());
    this.nextBtn?.addEventListener('click', () => this.goToNextStep());

    document.getElementById('wizard-form')?.addEventListener('submit', (e) => {
      e.preventDefault();
      this.handleSubmit();
    });

    // Auto-save draft on inputs
    document.getElementById('wizard-form')?.addEventListener('input', () => {
      if (!this.isEditMode) this.saveDraft();
    });

    // Photo file input
    this.photoInput?.addEventListener('change', (e) => this.handlePhotoFiles(e));

    // Clear draft button
    document.getElementById('clear-draft-btn')?.addEventListener('click', () => {
      if (confirm('Clear saved draft and start fresh?')) {
        localStorage.removeItem(DRAFT_KEY);
        window.location.reload();
      }
    });

    // Custom locality toggle
    const localitySelect = document.getElementById('locality-select');
    const customLocalityGroup = document.getElementById('custom-locality-group');
    localitySelect?.addEventListener('change', (e) => {
      if (e.target.value === '__custom__') {
        customLocalityGroup.style.display = 'block';
        document.getElementById('custom-locality-input').required = true;
      } else {
        customLocalityGroup.style.display = 'none';
        document.getElementById('custom-locality-input').required = false;
      }
    });
  }

  updateStepUI() {
    this.stepContainers.forEach((el, index) => {
      el.style.display = index + 1 === this.currentStep ? 'block' : 'none';
    });

    const percent = ((this.currentStep - 1) / (this.totalSteps - 1)) * 100;
    if (this.progressBar) this.progressBar.style.width = `${percent}%`;
    if (this.stepIndicator) this.stepIndicator.textContent = `Step ${this.currentStep} of ${this.totalSteps}`;

    if (this.prevBtn) {
      this.prevBtn.style.visibility = this.currentStep > 1 ? 'visible' : 'hidden';
    }

    if (this.currentStep === this.totalSteps) {
      if (this.nextBtn) this.nextBtn.style.display = 'none';
      if (this.submitBtn) this.submitBtn.style.display = 'inline-flex';
    } else {
      if (this.nextBtn) this.nextBtn.style.display = 'inline-flex';
      if (this.submitBtn) this.submitBtn.style.display = 'none';
    }

    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  validateCurrentStep() {
    const currentContainer = document.querySelector(`.wizard-step[data-step="${this.currentStep}"]`);
    if (!currentContainer) return true;

    const inputs = currentContainer.querySelectorAll('input, select, textarea');
    for (const input of inputs) {
      if (!input.checkValidity()) {
        input.reportValidity();
        return false;
      }
    }

    // Custom step 5 photo count check
    if (this.currentStep === 5) {
      if (this.photos.length < 2) {
        window.NestFinder?.showToast('Please upload at least 2 photos before submitting.', 'error');
        return false;
      }
    }

    return true;
  }

  goToNextStep() {
    if (this.validateCurrentStep()) {
      if (this.currentStep < this.totalSteps) {
        this.currentStep++;
        this.updateStepUI();
      }
    }
  }

  goToPrevStep() {
    if (this.currentStep > 1) {
      this.currentStep--;
      this.updateStepUI();
    }
  }

  async handlePhotoFiles(event) {
    const files = Array.from(event.target.files || []);
    if (!files.length) return;

    if (this.photos.length + files.length > 8) {
      window.NestFinder?.showToast('Maximum 8 photos allowed.', 'error');
      return;
    }

    this.uploadProgress.style.display = 'block';
    this.uploadProgressBar.style.width = '0%';

    for (let i = 0; i < files.length; i++) {
      try {
        const file = files[i];
        const uploadedUrl = await uploadPhotoToCloudinary(file, (percent) => {
          this.uploadProgressBar.style.width = `${percent}%`;
        });
        this.photos.push(uploadedUrl);
        this.renderPhotos();
        if (!this.isEditMode) this.saveDraft();
      } catch (err) {
        console.error('Photo upload failed:', err);
        window.NestFinder?.showToast(err.message || 'Upload failed. Please retry.', 'error');
      }
    }

    this.uploadProgress.style.display = 'none';
    this.photoInput.value = '';
  }

  renderPhotos() {
    if (!this.photosGrid) return;
    this.photosGrid.innerHTML = '';

    this.photos.forEach((url, index) => {
      const card = document.createElement('div');
      card.style.cssText = 'position:relative;border-radius:8px;overflow:hidden;border:1px solid var(--border);aspect-ratio:4/3;background:#eee;';
      card.innerHTML = `
        <img src="${url}" style="width:100%;height:100%;object-fit:cover;" alt="Photo ${index + 1}">
        ${index === 0 ? '<span style="position:absolute;top:4px;left:4px;background:var(--primary);color:#fff;font-size:0.65rem;font-weight:700;padding:2px 6px;border-radius:4px;">Cover Photo</span>' : ''}
        <div style="position:absolute;bottom:4px;right:4px;display:flex;gap:4px;">
          ${index > 0 ? `<button type="button" class="btn btn-secondary btn-sm btn-move" data-index="${index}" style="padding:2px 6px;font-size:0.7rem;" title="Move left">←</button>` : ''}
          <button type="button" class="btn btn-danger btn-sm btn-delete" data-index="${index}" style="padding:2px 6px;font-size:0.7rem;" title="Remove">&times;</button>
        </div>
      `;

      card.querySelector('.btn-delete')?.addEventListener('click', () => {
        this.photos.splice(index, 1);
        this.renderPhotos();
        if (!this.isEditMode) this.saveDraft();
      });

      card.querySelector('.btn-move')?.addEventListener('click', () => {
        const temp = this.photos[index - 1];
        this.photos[index - 1] = this.photos[index];
        this.photos[index] = temp;
        this.renderPhotos();
        if (!this.isEditMode) this.saveDraft();
      });

      this.photosGrid.appendChild(card);
    });

    document.getElementById('photo-count-indicator').textContent = `${this.photos.length}/8 photos added`;
  }

  collectFormData() {
    const form = document.getElementById('wizard-form');
    const fd = new FormData(form);

    const localitySelect = fd.get('locality');
    const isCustom = localitySelect === '__custom__';
    const locality = isCustom ? fd.get('customLocality') : localitySelect;

    const amenities = Array.from(form.querySelectorAll('input[name="amenities"]:checked')).map(el => el.value);

    return {
      title: fd.get('title'),
      description: fd.get('description'),
      type: fd.get('type'),
      rentPerMonth: parseFloat(fd.get('rentPerMonth') || '0'),
      securityDeposit: parseFloat(fd.get('securityDeposit') || '0'),
      furnishing: fd.get('furnishing'),
      bedrooms: parseInt(fd.get('bedrooms') || '1', 10),
      bathrooms: parseInt(fd.get('bathrooms') || '1', 10),
      genderPreference: fd.get('genderPreference'),
      availableFrom: fd.get('availableFrom'),
      locality: locality,
      localityIsCustom: isCustom,
      fullAddress: fd.get('fullAddress'),
      distanceFromOfficeKm: fd.get('distanceFromOfficeKm') ? parseFloat(fd.get('distanceFromOfficeKm')) : null,
      amenities: amenities,
      photos: this.photos,
      ownerName: fd.get('ownerName'),
      ownerPhone: fd.get('ownerPhone'),
      whatsappNumber: fd.get('whatsappNumber') || null,
    };
  }

  saveDraft() {
    try {
      const data = this.collectFormData();
      localStorage.setItem(DRAFT_KEY, JSON.stringify(data));
    } catch (_) {}
  }

  restoreDraft() {
    try {
      const draftJson = localStorage.getItem(DRAFT_KEY);
      if (draftJson) {
        const draft = JSON.parse(draftJson);
        this.populateData(draft);
        window.NestFinder?.showToast('Restored saved listing draft from your browser.', 'info');
      }
    } catch (_) {}
  }

  populateData(data) {
    const form = document.getElementById('wizard-form');
    if (!form) return;

    for (const [key, value] of Object.entries(data)) {
      if (key === 'photos') {
        this.photos = Array.isArray(value) ? [...value] : [];
        this.renderPhotos();
      } else if (key === 'amenities' && Array.isArray(value)) {
        value.forEach(am => {
          const chk = form.querySelector(`input[name="amenities"][value="${am}"]`);
          if (chk) chk.checked = true;
        });
      } else if (key === 'locality') {
        const select = document.getElementById('locality-select');
        const customGroup = document.getElementById('custom-locality-group');
        const customInput = document.getElementById('custom-locality-input');

        let matched = false;
        if (select) {
          for (const opt of select.options) {
            if (opt.value === value) {
              select.value = value;
              matched = true;
              break;
            }
          }
          if (!matched && value) {
            select.value = '__custom__';
            customGroup.style.display = 'block';
            customInput.value = value;
          }
        }
      } else {
        const input = form.querySelector(`[name="${key}"]`);
        if (input && value !== null && value !== undefined) {
          input.value = value;
        }
      }
    }
  }

  async handleSubmit() {
    if (!this.validateCurrentStep()) return;

    this.submitBtn.disabled = true;
    this.submitBtn.textContent = 'Saving Listing...';

    const payload = this.collectFormData();
    const endpoint = this.isEditMode ? `/listings/${this.listingId}/edit` : '/listings/new';
    const csrfToken = window.NestFinder?.getCsrfToken() || '';

    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken,
        },
        body: JSON.stringify(payload),
      });

      const result = await response.json();
      if (!response.ok) {
        if (result.errors) {
          const firstErr = Object.values(result.errors)[0];
          throw new Error(firstErr);
        }
        throw new Error(result.error || 'Failed to save listing');
      }

      localStorage.removeItem(DRAFT_KEY);
      window.location.href = result.redirect || `/listings/${result.listingId}`;
    } catch (err) {
      console.error('Submission error:', err);
      window.NestFinder?.showToast(err.message, 'error');
      this.submitBtn.disabled = false;
      this.submitBtn.textContent = this.isEditMode ? 'Save Changes' : 'Submit Listing';
    }
  }
}

document.addEventListener('DOMContentLoaded', () => {
  if (document.getElementById('wizard-form')) {
    window.listingWizard = new ListingWizard();
  }
});
