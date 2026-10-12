import 'package:cloud_firestore/cloud_firestore.dart';
import '../../../core/config/app_config.dart';

class AppConfigModel {
  final List<String> localities;
  final List<String> amenities;
  final String officeName;
  final double officeLatitude;
  final double officeLongitude;
  final Map<String, String> propertyTypeLabels;
  final Map<String, bool> propertyTypeEnabled;

  const AppConfigModel({
    required this.localities,
    required this.amenities,
    required this.officeName,
    required this.officeLatitude,
    required this.officeLongitude,
    required this.propertyTypeLabels,
    required this.propertyTypeEnabled,
  });

  factory AppConfigModel.defaults() {
    return AppConfigModel(
      localities: List.from(AppConfig.defaultLocalities),
      amenities: List.from(AppConfig.defaultAmenities),
      officeName: AppConfig.officeName,
      officeLatitude: AppConfig.officeLatitude,
      officeLongitude: AppConfig.officeLongitude,
      propertyTypeLabels: {
        'flat': 'Apartment / Flat',
        'house': 'Independent House',
        'room': 'Single Room',
        'pg': 'Paying Guest (PG)',
        'hostel': 'Hostel',
      },
      propertyTypeEnabled: {
        'flat': true,
        'house': true,
        'room': true,
        'pg': true,
        'hostel': true,
      },
    );
  }

  factory AppConfigModel.fromDocument(DocumentSnapshot<Map<String, dynamic>> doc) {
    if (!doc.exists || doc.data() == null) return AppConfigModel.defaults();
    final data = doc.data()!;

    final locs = (data['localities'] as List<dynamic>?)
            ?.map((e) => e.toString().trim())
            .where((e) => e.isNotEmpty)
            .toList() ??
        AppConfig.defaultLocalities;

    final amens = (data['amenities'] as List<dynamic>?)
            ?.map((e) => e.toString().trim())
            .where((e) => e.isNotEmpty)
            .toList() ??
        AppConfig.defaultAmenities;

    final rawLabels = data['propertyTypeLabels'] as Map<String, dynamic>? ?? {};
    final defaultLabels = {
      'flat': 'Apartment / Flat',
      'house': 'Independent House',
      'room': 'Single Room',
      'pg': 'Paying Guest (PG)',
      'hostel': 'Hostel',
    };
    final labels = <String, String>{};
    for (final entry in defaultLabels.entries) {
      labels[entry.key] = rawLabels[entry.key]?.toString() ?? entry.value;
    }

    final rawEnabled = data['propertyTypeEnabled'] as Map<String, dynamic>? ?? {};
    final enabled = <String, bool>{};
    for (final k in defaultLabels.keys) {
      enabled[k] = rawEnabled[k] as bool? ?? true;
    }

    return AppConfigModel(
      localities: locs,
      amenities: amens,
      officeName: data['officeName'] as String? ?? AppConfig.officeName,
      officeLatitude: (data['officeLatitude'] as num?)?.toDouble() ?? AppConfig.officeLatitude,
      officeLongitude: (data['officeLongitude'] as num?)?.toDouble() ?? AppConfig.officeLongitude,
      propertyTypeLabels: labels,
      propertyTypeEnabled: enabled,
    );
  }

  Map<String, dynamic> toMap() {
    return {
      'localities': localities,
      'amenities': amenities,
      'officeName': officeName,
      'officeLatitude': officeLatitude,
      'officeLongitude': officeLongitude,
      'propertyTypeLabels': propertyTypeLabels,
      'propertyTypeEnabled': propertyTypeEnabled,
    };
  }

  AppConfigModel copyWith({
    List<String>? localities,
    List<String>? amenities,
    String? officeName,
    double? officeLatitude,
    double? officeLongitude,
    Map<String, String>? propertyTypeLabels,
    Map<String, bool>? propertyTypeEnabled,
  }) {
    return AppConfigModel(
      localities: localities ?? this.localities,
      amenities: amenities ?? this.amenities,
      officeName: officeName ?? this.officeName,
      officeLatitude: officeLatitude ?? this.officeLatitude,
      officeLongitude: officeLongitude ?? this.officeLongitude,
      propertyTypeLabels: propertyTypeLabels ?? this.propertyTypeLabels,
      propertyTypeEnabled: propertyTypeEnabled ?? this.propertyTypeEnabled,
    );
  }
}
