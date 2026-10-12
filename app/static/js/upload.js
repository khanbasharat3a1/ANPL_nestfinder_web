/**
 * Client-Side Image Compression and Cloudinary Direct Signed Upload
 * Compresses images with HTML5 Canvas to max 1280px and ~400KB.
 * Signs upload parameters via /api/uploads/sign without exposing secrets.
 */

export async function compressImage(file, maxWidth = 1280, quality = 0.8) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = reject;
    reader.onload = (e) => {
      const img = new Image();
      img.onerror = reject;
      img.onload = () => {
        let width = img.width;
        let height = img.height;

        if (width > maxWidth) {
          height = Math.round((height * maxWidth) / width);
          width = maxWidth;
        }

        const canvas = document.createElement('canvas');
        canvas.width = width;
        canvas.height = height;

        const ctx = canvas.getContext('2d');
        ctx.drawImage(img, 0, 0, width, height);

        canvas.toBlob(
          (blob) => {
            if (blob) {
              resolve(blob);
            } else {
              reject(new Error('Canvas image compression failed'));
            }
          },
          'image/jpeg',
          quality
        );
      };
      img.src = e.target.result;
    };
    reader.readAsDataURL(file);
  });
}

/**
 * Requests an authenticated upload signature from the web server.
 */
async function fetchUploadSignature() {
  const csrfToken = window.NestFinder?.getCsrfToken() || '';
  const response = await fetch('/api/uploads/sign', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrfToken,
    },
  });

  if (!response.ok) {
    const err = await response.json();
    throw new Error(err.error || 'Failed to authorize image upload');
  }

  return await response.json();
}

/**
 * Uploads a compressed image directly to Cloudinary with progress callback.
 */
export async function uploadPhotoToCloudinary(file, onProgress) {
  // 1. Compress image in browser
  const compressedBlob = await compressImage(file);

  // 2. Fetch signed parameters from backend
  const signData = await fetchUploadSignature();

  // 3. Prepare FormData
  const formData = new FormData();
  formData.append('file', compressedBlob, file.name || 'photo.jpg');
  formData.append('api_key', signData.apiKey);
  formData.append('timestamp', signData.timestamp);
  formData.append('signature', signData.signature);
  formData.append('folder', signData.folder);
  formData.append('upload_preset', signData.uploadPreset);

  const endpoint = `https://api.cloudinary.com/v1_1/${signData.cloudName}/image/upload`;

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', endpoint);

    if (onProgress && xhr.upload) {
      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable) {
          const percent = Math.round((e.loaded / e.total) * 100);
          onProgress(percent);
        }
      };
    }

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const result = JSON.parse(xhr.responseText);
          resolve(result.secure_url);
        } catch (e) {
          reject(new Error('Failed to parse Cloudinary response'));
        }
      } else {
        try {
          const errorResp = JSON.parse(xhr.responseText);
          reject(new Error(errorResp.error?.message || 'Cloudinary upload failed'));
        } catch (_) {
          reject(new Error(`Upload failed with HTTP ${xhr.status}`));
        }
      }
    };

    xhr.onerror = () => reject(new Error('Network error during image upload'));
    xhr.send(formData);
  });
}
