import 'package:flutter/material.dart';
import '../constants/app_colors.dart';

/// Represents the status lifecycle of a listing.
enum ListingStatus {
  pending('pending', 'Pending Approval'),
  approved('approved', 'Approved'),
  rejected('rejected', 'Rejected'),
  archived('archived', 'Archived');

  final String value;
  final String label;

  const ListingStatus(this.value, this.label);

  static ListingStatus fromString(String? status) {
    switch (status) {
      case 'approved':
        return ListingStatus.approved;
      case 'rejected':
        return ListingStatus.rejected;
      case 'archived':
        return ListingStatus.archived;
      case 'pending':
      default:
        return ListingStatus.pending;
    }
  }

  Color get color {
    switch (this) {
      case ListingStatus.pending:
        return AppColors.statusPending;
      case ListingStatus.approved:
        return AppColors.statusApproved;
      case ListingStatus.rejected:
        return AppColors.statusRejected;
      case ListingStatus.archived:
        return AppColors.statusArchived;
    }
  }

  Color get backgroundColor {
    switch (this) {
      case ListingStatus.pending:
        return AppColors.statusPendingBg;
      case ListingStatus.approved:
        return AppColors.statusApprovedBg;
      case ListingStatus.rejected:
        return AppColors.statusRejectedBg;
      case ListingStatus.archived:
        return AppColors.statusArchivedBg;
    }
  }

  IconData get icon {
    switch (this) {
      case ListingStatus.pending:
        return Icons.access_time_rounded;
      case ListingStatus.approved:
        return Icons.check_circle_rounded;
      case ListingStatus.rejected:
        return Icons.cancel_rounded;
      case ListingStatus.archived:
        return Icons.archive_rounded;
    }
  }
}
