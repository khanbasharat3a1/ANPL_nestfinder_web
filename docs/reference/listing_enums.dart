import 'package:flutter/material.dart';
import '../constants/app_colors.dart';

/// Types of accommodation available in Billawar
enum PropertyType {
  flat('flat', 'Flat / Apartment', Icons.apartment_rounded),
  house('house', 'Independent House', Icons.home_rounded),
  room('room', 'Single / Shared Room', Icons.meeting_room_rounded),
  pg('pg', 'PG (Paying Guest)', Icons.hotel_rounded),
  hostel('hostel', 'Hostel', Icons.night_shelter_rounded);

  final String value;
  final String label;
  final IconData icon;

  const PropertyType(this.value, this.label, this.icon);

  static PropertyType fromString(String? val) {
    return PropertyType.values.firstWhere(
      (e) => e.value.toLowerCase() == val?.toLowerCase(),
      orElse: () => PropertyType.flat,
    );
  }
}

/// Furnishing status of the property
enum FurnishingType {
  furnished('furnished', 'Fully Furnished'),
  semi('semi', 'Semi Furnished'),
  unfurnished('unfurnished', 'Unfurnished');

  final String value;
  final String label;

  const FurnishingType(this.value, this.label);

  static FurnishingType fromString(String? val) {
    return FurnishingType.values.firstWhere(
      (e) => e.value.toLowerCase() == val?.toLowerCase(),
      orElse: () => FurnishingType.semi,
    );
  }
}

/// Gender preference for tenants
enum GenderPreference {
  any('any', 'Anyone (Male / Female / Family)'),
  male('male', 'Male Only'),
  female('female', 'Female Only');

  final String value;
  final String label;

  const GenderPreference(this.value, this.label);

  static GenderPreference fromString(String? val) {
    return GenderPreference.values.firstWhere(
      (e) => e.value.toLowerCase() == val?.toLowerCase(),
      orElse: () => GenderPreference.any,
    );
  }
}

/// Approval status lifecycle for a property listing
enum ListingStatus {
  pending('pending', 'Pending Approval', AppColors.statusPending, AppColors.statusPendingBg),
  approved('approved', 'Approved', AppColors.statusApproved, AppColors.statusApprovedBg),
  rejected('rejected', 'Rejected', AppColors.statusRejected, AppColors.statusRejectedBg),
  archived('archived', 'Archived', AppColors.statusArchived, AppColors.statusArchivedBg);

  final String value;
  final String label;
  final Color color;
  final Color backgroundColor;

  const ListingStatus(this.value, this.label, this.color, this.backgroundColor);

  static ListingStatus fromString(String? val) {
    return ListingStatus.values.firstWhere(
      (e) => e.value.toLowerCase() == val?.toLowerCase(),
      orElse: () => ListingStatus.pending,
    );
  }
}
