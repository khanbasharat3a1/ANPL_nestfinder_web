# NestFinder Web — Data Contract & Backend Specification
**Document Version:** 1.0.0  
**Target Environment:** Firebase Firestore (`asia-south1`) & Cloudinary (`khan-developers`)  
**Shared Codebase Reference:** Flutter Android Client (`ANPL2_gemini`)

---

## 1. Overview & Source of Truth Architecture

NestFinder is a shared accommodation discovery platform for **Atomic North Pvt Ltd** (Billawar, Jammu and Kashmir). Both the Flutter Android mobile application and the Python/Flask web companion share the identical Firebase project (`atomic-north-accommodation-hub`) and Cloudinary storage account (`khan-developers`).

### Core Tenets
1. **Source of Truth:** The Flutter reference code (`docs/reference/`) defines the exact schema, field types, and lifecycle behavior. Any discrepancies between requirements and reference code are resolved in favor of the reference code.
2. **Read-Only Reference:** Files within `docs/reference/` are strictly read-only. Firestore rules (`firestore.rules`) and composite indexes (`firestore.indexes.json`) are managed solely from the Flutter project.
3. **No Firestore Rules Bypass for Logic:** While the web backend uses `firebase-admin` with a service account (bypassing Firestore client security rules), the server must strictly enforce equivalent or stricter authorization in `app/services/policy.py`.
4. **Deny-by-Default Authorization:** Normal users can only read `approved` and non-archived listings (`status == 'approved' && isArchived == false`), plus their own listings. Approvers and super admins may inspect pending listings.

---

## 2. Firestore Collections & Data Schemas

### 2.1 Collection: `users`
- **Document Path:** `users/{uid}`
- **Document ID:** Firebase Auth UID (`request.auth.uid`).
- **Description:** User profile and role document. Created on initial sign-up / sign-in if not present.

| Field Name | Type | Required / Optional | Allowed Values / Constraints | Default Value | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `name` | String | Required | 1–100 chars | `'Employee'` | User's display name |
| `nameLower` | String | Required | Lowercase string | `name.toLowerCase()` | Indexed for search prefix queries |
| `email` | String | Required | Valid email string | `''` | User's primary email address |
| `emailLower` | String | Required | Lowercase string | `email.toLowerCase()` | Indexed for search prefix queries |
| `phone` | String | Optional | Nullable, 10-digit Indian phone (e.g. `9876543210`) | `null` | Sanitized without `+91` |
| `photoUrl` | String | Optional | Nullable URL string | `null` | Profile avatar URL |
| `role` | String | Required | `'user'`, `'approver'`, `'super_admin'` | `'user'` | Enforced by security rules |
| `isBanned` | Boolean | Required | `true`, `false` | `false` | Banned users cannot access app |
| `fcmToken` | String | Optional | Nullable string | `null` | Android FCM push token (mobile only) |
| `createdAt` | Timestamp | Required | Server timestamp / ISO datetime | `now()` | Immutable registration timestamp |

---

### 2.2 Subcollection: `users/{uid}/favorites`
- **Document Path:** `users/{uid}/favorites/{listingId}`
- **Document ID:** Listing ID (`listingId`).
- **Description:** User bookmarks / favorites. Existence of document indicates listing is favorited.

| Field Name | Type | Required / Optional | Allowed Values / Constraints | Default Value | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `listingId` | String | Required | Existing listing document ID | Path ID | Redundant key for sanity |
| `savedAt` | Timestamp | Required | Timestamp | `FieldValue.serverTimestamp()` | Timestamp bookmark was added |

---

### 2.3 Subcollection: `users/{uid}/notifications`
- **Document Path:** `users/{uid}/notifications/{notificationId}`
- **Document ID:** Auto-generated Firestore ID (`doc().id`).
- **Description:** In-app notifications generated on listing approval, rejection, or takedown.

| Field Name | Type | Required / Optional | Allowed Values / Constraints | Default Value | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `type` | String | Required | `'approved'`, `'rejected'` | `'approved'` | Notification category |
| `listingId` | String | Required | Valid listing document ID | — | Target listing |
| `listingTitle` | String | Required | Listing title (snapshot) | — | Cached title for display |
| `message` | String | Required | Non-empty string | — | Human-readable body |
| `rejectionReason`| String | Optional | Non-empty string if `type == 'rejected'` | `null` | Present on rejection |
| `createdAt` | Timestamp | Required | Timestamp | `FieldValue.serverTimestamp()` | Creation time |
| `read` | Boolean | Required | `true`, `false` | `false` | Read status (owner can toggle) |

---

### 2.4 Collection: `listings`
- **Document Path:** `listings/{listingId}`
- **Document ID:** Auto-generated unique string ID (`doc().id`).
- **Description:** Primary accommodation listings directory.

| Field Name | Type | Required / Optional | Allowed Values / Constraints | Default Value | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `ownerId` | String | Required | UID of listing creator | Current Auth UID | Immutable after creation |
| `ownerName` | String | Required | Non-empty string | — | Contact person name |
| `ownerPhone` | String | Required | 10-digit Indian phone (`^[6-9]\d{9}$`) | — | Primary contact number |
| `whatsappNumber` | String | Optional | Nullable, 10-digit Indian phone | `null` | Falls back to `ownerPhone` for chats |
| `title` | String | Required | 5–100 characters | — | Headline |
| `description` | String | Required | 10–2000 characters | — | Detailed property description |
| `type` | String | Required | `'flat'`, `'house'`, `'room'`, `'pg'`, `'hostel'` | `'flat'` | Accommodation type enum |
| `rentPerMonth` | Number | Required | `rentPerMonth > 0` (Float/Int) | `0.0` | Monthly rent in INR |
| `securityDeposit`| Number | Required | `securityDeposit >= 0` (Float/Int) | `0.0` | Security deposit in INR |
| `furnishing` | String | Required | `'furnished'`, `'semi'`, `'unfurnished'` | `'semi'` | Furnishing status enum |
| `bedrooms` | Integer | Required | Integer $\ge 0$ | `1` | Bedroom count (0 for 1RK/room) |
| `bathrooms` | Integer | Required | Integer $\ge 1$ | `1` | Bathroom count |
| `genderPreference`| String | Required | `'any'`, `'male'`, `'female'` | `'any'` | Tenant preference |
| `availableFrom` | Timestamp | Required | Timestamp | — | Move-in date |
| `locality` | String | Required | 1–60 chars (per Firestore rules) | — | e.g. "Billawar Main Bazar" |
| `localityIsCustom`| Boolean | Required | `true`, `false` | `false` | True if entered outside preset list |
| `fullAddress` | String | Required | Non-empty address string | — | Physical street address |
| `lat` | Number | Optional | Nullable coordinate | `null` | GPS latitude |
| `lng` | Number | Optional | Nullable coordinate | `null` | GPS longitude |
| `amenities` | Array\<String\>| Required | List of strings from preset or custom | `[]` | Amenities tags |
| `photos` | Array\<String\>| Required | 2 to 8 items, starting with Cloudinary prefix | `[]` | `https://res.cloudinary.com/khan-developers/` |
| `coverPhoto` | String | Required | Must match first photo in `photos` | `photos[0]` | Primary display image |
| `status` | String | Required | `'pending'`, `'approved'`, `'rejected'`, `'archived'` | `'pending'` | Lifecycle state |
| `isArchived` | Boolean | Required | `true`, `false` | `false` | Soft-deletion flag |
| `rejectionReason`| String | Optional | Non-empty string when rejected; deleted on approve | `null` | Reason communicated to owner |
| `reviewedBy` | String | Optional | UID of approver or super_admin | `null` | Reviewer UID |
| `reviewedByName` | String | Optional | Display name of reviewer | `null` | Reviewer name |
| `reviewedByRole` | String | Optional | `'Approver'`, `'super_admin'`, `'Super Admin'` | `null` | Role of reviewer at decision time |
| `reviewedAt` | Timestamp | Optional | Timestamp | `null` | Timestamp review took place |
| `createdAt` | Timestamp | Required | Timestamp | `FieldValue.serverTimestamp()` | Creation timestamp |
| `updatedAt` | Timestamp | Required | Timestamp | `FieldValue.serverTimestamp()` | Last modified timestamp |
| `distanceFromOfficeKm` | Number | Optional | Nullable float $\ge 0$ | `null` | Distance from Billawar HQ |

---

### 2.5 Collection: `reports`
- **Document Path:** `reports/{reportId}`
- **Document ID:** Deterministic composite ID: `${listingId}_${reportedBy}`.
- **Description:** Community reports flagging inaccurate, offensive, or unavailable accommodations.

| Field Name | Type | Required / Optional | Allowed Values / Constraints | Default Value | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `listingId` | String | Required | Listing document ID | — | Target listing ID |
| `listingTitle` | String | Required | Title of listing at time of report | — | Cached for quick admin inbox scan |
| `reportedBy` | String | Required | UID of reporting user | Current Auth UID | Reporter UID |
| `reporterName` | String | Required | Display name of reporter | `'User'` | Reporter display name |
| `reason` | String | Required | Non-empty text reason | — | Details of complaint |
| `status` | String | Required | `'open'`, `'resolved'` | `'open'` | Status per repository and index |
| `createdAt` | Timestamp | Required | Timestamp | `FieldValue.serverTimestamp()` | Submission timestamp |
| `resolvedAt` | Timestamp | Optional | Timestamp | `null` | Timestamp report was dismissed/takedown |
| `resolvedBy` | String | Optional | UID of super_admin | `null` | Admin who resolved report |

---

### 2.6 Collection: `adminLogs`
- **Document Path:** `adminLogs/{logId}`
- **Document ID:** Auto-generated Firestore ID (`doc().id`).
- **Description:** Immutable, append-only administrative audit log.

| Field Name | Type | Required / Optional | Allowed Values / Constraints | Default Value | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `actorUid` | String | Required | UID of the user performing the privileged action | Current Auth UID | Who did it |
| `action` | String | Required | Standardized action verb (see 3.8) | — | Categorized audit action |
| `targetId` | String | Required | Document ID, `'multiple'`, or collection path | — | Target resource ID |
| `details` | String | Required | Detailed human-readable description | — | Changes, diffs, or explanation |
| `createdAt` | Timestamp | Required | Timestamp | `FieldValue.serverTimestamp()` | Action timestamp |

---

### 2.7 Document: `config/app`
- **Document Path:** `config/app`
- **Document ID:** Single static document `app`.
- **Description:** Global application configurations, localities, office coordinates, and property metadata.

| Field Name | Type | Required / Optional | Allowed Values / Constraints | Default Value | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `localities` | Array\<String\>| Required | List of allowed locality strings | Default 7 localities | Preset localities in Billawar |
| `amenities` | Array\<String\>| Required | List of allowed amenity strings | Default 12 amenities | Preset amenity checkboxes |
| `officeName` | String | Required | Non-empty string | `'Atomic North Campus, Billawar'` | Billawar HQ name |
| `officeLatitude` | Number | Required | Latitude float | `32.6105` | Billawar HQ Lat |
| `officeLongitude`| Number | Required | Longitude float | `75.6027` | Billawar HQ Lng |
| `propertyTypeLabels` | Map\<String, String\>| Required | Keys: `flat`, `house`, `room`, `pg`, `hostel` | Standard user-facing labels | Rebranding & UI labels |
| `propertyTypeEnabled`| Map\<String, Boolean\>| Required | Keys: `flat`, `house`, `room`, `pg`, `hostel` | All `true` | Allows toggling types on/off |

---

## 3. Action Lifecycle & Write Semantics

### 3.1 Listing Creation
- **Trigger:** Normal User, Approver, or Super Admin creates a listing.
- **Normal User Behavior:**
  - `status`: `'pending'`
  - `isArchived`: `false`
  - `reviewedBy`: `null`
  - `reviewedByName`: `null`
  - `reviewedByRole`: `null`
  - `reviewedAt`: `null`
  - `createdAt`: `FieldValue.serverTimestamp()`
  - `updatedAt`: `FieldValue.serverTimestamp()`
- **Approver or Super Admin Behavior (Auto-Approved):**
  - `status`: `'approved'`
  - `isArchived`: `false`
  - `reviewedBy`: `current_user.uid`
  - `reviewedByName`: `current_user.name`
  - `reviewedByRole`: `'Approver'` or `'Super Admin'` (matching user's actual role)
  - `reviewedAt`: `FieldValue.serverTimestamp()`
  - `createdAt`: `FieldValue.serverTimestamp()`
  - `updatedAt`: `FieldValue.serverTimestamp()`

### 3.2 Listing Edit (Owner Resubmission)
- **Pending or Rejected Listing:**
  - Owner updates fields.
  - `status`: `'pending'`
  - `rejectionReason`: Removed (`FieldValue.delete()` or `null`)
  - `updatedAt`: `FieldValue.serverTimestamp()`
- **Approved Listing:**
  - Editing key listing details automatically resets `status` to `'pending'` (mirroring Flutter app and Firestore security rules line 169).
  - Must go back through review queue before becoming public again.

### 3.3 Listing Approval (Review Queue)
- **Trigger:** Approver (on pending listing not owned by self) or Super Admin.
- **Atomic Batch Write:**
  1. **Update `listings/{listingId}`:**
     - `status`: `'approved'`
     - `reviewedBy`: `reviewer.uid`
     - `reviewedByName`: `reviewer.name`
     - `reviewedByRole`: `reviewer.role` (`'Approver'` or `'Super Admin'`)
     - `reviewedAt`: `FieldValue.serverTimestamp()`
     - `rejectionReason`: `FieldValue.delete()`
     - `updatedAt`: `FieldValue.serverTimestamp()`
     - *Optional Minor Edits:* Approver can update `title`, `description`, `amenities`, `locality`, `localityIsCustom`, `distanceFromOfficeKm` in this same write.
  2. **Create `users/{ownerId}/notifications/{notifId}`:**
     - `type`: `'approved'`
     - `listingId`: `listingId`
     - `listingTitle`: `finalTitle`
     - `message`: `'Your listing "' + finalTitle + '" has been approved and is now live on Explore.'`
     - `createdAt`: `FieldValue.serverTimestamp()`
     - `read`: `false`
  3. **Append `adminLogs`:**
     - `actorUid`: `reviewer.uid`
     - `action`: `'approve_listing'` (or `'force_approve'` for admin)
     - `targetId`: `listingId`
     - `details`: `'Approved listing "' + finalTitle + '"'`
     - `createdAt`: `FieldValue.serverTimestamp()`

### 3.4 Listing Rejection
- **Trigger:** Approver or Super Admin rejects a pending listing.
- **Validation:** `rejectionReason` is strictly required and non-empty.
- **Atomic Batch Write:**
  1. **Update `listings/{listingId}`:**
     - `status`: `'rejected'`
     - `rejectionReason`: `reason`
     - `reviewedBy`: `reviewer.uid`
     - `reviewedByName`: `reviewer.name`
     - `reviewedByRole`: `reviewer.role`
     - `reviewedAt`: `FieldValue.serverTimestamp()`
     - `updatedAt`: `FieldValue.serverTimestamp()`
  2. **Create `users/{ownerId}/notifications/{notifId}`:**
     - `type`: `'rejected'`
     - `listingId`: `listingId`
     - `listingTitle`: `title`
     - `message`: `'Your listing "' + title + '" was not approved: ' + reason`
     - `rejectionReason`: `reason`
     - `createdAt`: `FieldValue.serverTimestamp()`
     - `read`: `false`
  3. **Append `adminLogs`:**
     - `actorUid`: `reviewer.uid`
     - `action`: `'reject_listing'`
     - `targetId`: `listingId`
     - `details`: `'Rejected listing: ' + reason`
     - `createdAt`: `FieldValue.serverTimestamp()`

### 3.5 Archiving & Deletion
- **Owner Archival (Withdraw / Soft-Delete):**
  - Update `listings/{listingId}`: `isArchived = true`, `status = 'archived'`, `updatedAt = serverTimestamp()`.
- **Super Admin Takedown / Force Archive:**
  - Updates `isArchived = true`, `status = 'archived'`.
  - Writes audit log: `archive_listing`.
- **Super Admin Permanent Delete:**
  - Deletes document from `listings/{listingId}`.
  - Initiates best-effort background Cloudinary photo deletion for all associated photos (`listings/<ownerId>/...`).
  - Writes audit log: `delete_listing`.

### 3.6 Favorites Management
- **Add Favorite:** `set()` on `users/{uid}/favorites/{listingId}` with `{listingId, savedAt}`.
- **Remove Favorite:** `delete()` on `users/{uid}/favorites/{listingId}`.

### 3.7 Community Reporting & Takedown
- **Report Submission:**
  - User submits report. Document set at `reports/{listingId}_{reportedBy}`:
    `{listingId, listingTitle, reportedBy, reporterName, reason, status: 'open', createdAt: serverTimestamp()}`.
  - Deterministic ID guarantees one report per user per listing.
- **Report Dismissal (Super Admin):**
  - Update `reports/{id}`: `status = 'resolved'`, `resolvedAt = serverTimestamp()`, `resolvedBy = adminUid`.
  - Audit log: `dismiss_report`.
- **Report Takedown (Super Admin):**
  - Atomic Batch:
    1. Update `listings/{listingId}`: `isArchived = true`, `status = 'archived'`, `updatedAt = serverTimestamp()`.
    2. Update `reports/{id}`: `status = 'resolved'`, `resolvedAt = serverTimestamp()`, `resolvedBy = adminUid`.
    3. Create `users/{ownerId}/notifications/{notifId}`: `type = 'rejected'`, takedown notice.
    4. Audit log: `takedown_report`.

### 3.8 Audit Log Actions Catalog
All privileged operations produce an immutable record in `adminLogs`:

| Action Code | Actor | Description & Target |
| :--- | :--- | :--- |
| `approve_listing` | Approver | Approved a listing from the review queue |
| `reject_listing` | Approver | Rejected a listing with required reason |
| `minor_edit_listing` | Approver | Modified allowed fields prior to or alongside approval |
| `force_approve` | Super Admin | Admin direct approval outside normal queue |
| `force_reject` | Super Admin | Admin direct rejection |
| `archive_listing` | Super Admin | Admin archived a listing |
| `unarchive_listing` | Super Admin | Admin unarchived a listing |
| `delete_listing` | Super Admin | Permanently deleted a listing document |
| `bulk_approve` | Super Admin | Approved batch of listings ($\le 50$) |
| `bulk_reject` | Super Admin | Rejected batch of listings ($\le 50$) |
| `bulk_archive` | Super Admin | Archived batch of listings ($\le 50$) |
| `bulk_delete` | Super Admin | Deleted batch of listings ($\le 50$) |
| `role_change` | Super Admin | Modified user role (`user`, `approver`, `super_admin`) |
| `ban_user` | Super Admin | Banned a user |
| `unban_user` | Super Admin | Unbanned a user |
| `hide_user_listings` | Super Admin | Archived all listings owned by a banned user |
| `backfill_search_fields` | Super Admin | Backfilled `nameLower` and `emailLower` |
| `dismiss_report` | Super Admin | Dismissed report without modifying listing |
| `takedown_report` | Super Admin | Resolved report by archiving target listing |
| `update_app_config` | Super Admin | Updated `config/app` settings |

---

## 4. Query & Index Mapping

The web backend MUST strictly abide by the composite indexes defined in `firestore.indexes.json`:

1. **Explore Feed Queries (Approved & Non-Archived):**
   - Filter `status == 'approved'`, `isArchived == false`, ordered by `createdAt DESC`
   - Filter `status == 'approved'`, `isArchived == false`, ordered by `rentPerMonth ASC`
   - Filter `status == 'approved'`, `isArchived == false`, ordered by `rentPerMonth DESC`
   - Filter `status == 'approved'`, `isArchived == false`, `locality == X`, ordered by `createdAt DESC`
   - Filter `status == 'approved'`, `isArchived == false`, `locality == X`, ordered by `rentPerMonth ASC`
   - Filter `status == 'approved'`, `isArchived == false`, `locality == X`, ordered by `rentPerMonth DESC`
   - Filter `status == 'approved'`, `isArchived == false`, `type == X`, ordered by `createdAt DESC`
   - Filter `status == 'approved'`, `isArchived == false`, `furnishing == X`, ordered by `createdAt DESC`
   - Filter `status == 'approved'`, `isArchived == false`, `genderPreference == X`, ordered by `createdAt DESC`

2. **Review Queue Query:**
   - Filter `status == 'pending'`, ordered by `createdAt ASC` (oldest first).

3. **My Listings Queries:**
   - Filter `ownerId == uid`, ordered by `createdAt DESC`.
   - Filter `ownerId == uid`, `status == X`, ordered by `createdAt DESC`.
   - Filter `ownerId == uid`, `isArchived == false`, `status == X`, ordered by `createdAt DESC`.

4. **Admin Listings Management:**
   - Ordered by `createdAt DESC`, filtered optionally by `status` and/or `isArchived`.

5. **Reports Inbox:**
   - Filter `status == 'open'`, ordered by `createdAt DESC`.

---

## 5. Discrepancy Analysis: Section 2 Prompt vs Flutter Reference

The table below lists every discrepancy found between the prompt's Section 2 summary and the Flutter source code (`docs/reference/`):

| Area | Prompt Section 2 Summary | Flutter Reference Code (`docs/reference/`) | Resolution / Truth Adopted |
| :--- | :--- | :--- | :--- |
| **Listing Status Enum** | Listed as `(pending \| approved \| rejected)`. | `ListingStatus` in `listing_enums.dart`, `firestore.rules`, and `listings_repository.dart` includes `'archived'`. | Reference wins: `ListingStatus` has 4 valid values: `pending`, `approved`, `rejected`, `archived`. |
| **Report Model vs Storage** | Mentions `reports/{listingId_reporterUid}` without field details. | `report_model.dart` had `reportedByName` and `resolved: bool`. However, `reports_repository.dart`, `admin_repository.dart`, and `firestore.indexes.json` explicitly write and query `'reporterName'` and `'status'` (`'open'` / `'resolved'`). | Reference writing code wins: Store `reporterName`, `status: 'open'` / `'resolved'`, plus `resolvedAt`, `resolvedBy`. |
| **Favorites Schema** | Mentions `users/{uid}/favorites/{listingId}`. | `favorites_repository.dart` stores `{ 'listingId': listingId, 'savedAt': Timestamp.now() }`. | Reference wins: Store both `listingId` and `savedAt`. |
| **Cloudinary Upload Preset** | Prompt Section 6: `accommodation_signed` (signed). | `app_config.dart` in Flutter app: `accommodation_unsigned`. | As specified by Web Architecture: Web server generates signed upload signatures for `accommodation_signed` with `listings/<uid>` folder, keeping API secret on the server. |
| **Listing Page Size** | Prompt Section 5 specifies 12 listings per page with signed cursor tokens. | `app_config.dart` in Flutter app specifies 15. | Web uses 12 per prompt read budget requirement. |
| **Reviewer Role Storage** | Prompt Section 3 asks to check how `reviewedByRole` is stored. | `listings_repository.dart` stores `reviewerRole ?? 'Approver'` or string role; `admin_repository.dart` force approve leaves it optional. | Web sets `reviewedByRole` to string title: `'Approver'` or `'Super Admin'` matching the reviewer's active role. |
| **Locality Length Constraint** | Section 2 states `locality` without length constraint. | `firestore.rules` lines 132 & 156 enforce `locality.size() > 0 && locality.size() <= 60`. | Strict enforcement: Validate locality string $\le 60$ characters. |
| **Image URLs Validation** | Must use Cloudinary. | Host domain: `https://res.cloudinary.com/khan-developers/`. | Server rejects any image URL not originating from `https://res.cloudinary.com/khan-developers/`. |

---

## 6. Sign-off & Next Steps

This Data Contract establishes the boundary conditions for Stage 1 (Foundation Setup). No schema modifications may occur without explicit version incrementation and compatibility validation with the Android client.
