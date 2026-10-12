import 'package:cloud_firestore/cloud_firestore.dart';
import '../../../core/enums/listing_enums.dart';

/// Complete property listing model adhering to Firestore data schema.
class ListingModel {
  final String id;
  final String ownerId;
  final String ownerName;
  final String ownerPhone;
  final String? whatsappNumber;
  final String title;
  final String description;
  final PropertyType type;
  final double rentPerMonth;
  final double securityDeposit;
  final FurnishingType furnishing;
  final int bedrooms;
  final int bathrooms;
  final GenderPreference genderPreference;
  final DateTime availableFrom;
  final String locality;
  final bool localityIsCustom;
  final String fullAddress;
  final double? lat;
  final double? lng;
  final List<String> amenities;
  final List<String> photos;
  final String coverPhoto;
  final ListingStatus status;
  final String? rejectionReason;
  final String? reviewedBy;
  final String? reviewedByName;
  final String? reviewedByRole;
  final DateTime? reviewedAt;
  final DateTime createdAt;
  final DateTime updatedAt;
  final double? distanceFromOfficeKm;
  final bool isArchived;

  const ListingModel({
    required this.id,
    required this.ownerId,
    required this.ownerName,
    required this.ownerPhone,
    this.whatsappNumber,
    required this.title,
    required this.description,
    required this.type,
    required this.rentPerMonth,
    required this.securityDeposit,
    required this.furnishing,
    required this.bedrooms,
    required this.bathrooms,
    required this.genderPreference,
    required this.availableFrom,
    required this.locality,
    this.localityIsCustom = false,
    required this.fullAddress,
    this.lat,
    this.lng,
    required this.amenities,
    required this.photos,
    required this.coverPhoto,
    this.status = ListingStatus.pending,
    this.rejectionReason,
    this.reviewedBy,
    this.reviewedByName,
    this.reviewedByRole,
    this.reviewedAt,
    required this.createdAt,
    required this.updatedAt,
    this.distanceFromOfficeKm,
    this.isArchived = false,
  });

  /// Formatted rent string in INR format
  String get formattedRent {
    final rentInt = rentPerMonth.round();
    return '₹$rentInt/mo';
  }

  /// Formatted security deposit string in INR format
  String get formattedDeposit {
    final depositInt = securityDeposit.round();
    return '₹$depositInt';
  }

  /// WhatsApp contact number with priority for explicit WhatsApp field
  String get activeWhatsappNumber =>
      (whatsappNumber != null && whatsappNumber!.trim().isNotEmpty)
          ? whatsappNumber!.trim()
          : ownerPhone.trim();

  Map<String, dynamic> toMap() {
    return {
      'ownerId': ownerId,
      'ownerName': ownerName,
      'ownerPhone': ownerPhone,
      'whatsappNumber': whatsappNumber,
      'title': title,
      'description': description,
      'type': type.value,
      'rentPerMonth': rentPerMonth,
      'securityDeposit': securityDeposit,
      'furnishing': furnishing.value,
      'bedrooms': bedrooms,
      'bathrooms': bathrooms,
      'genderPreference': genderPreference.value,
      'availableFrom': Timestamp.fromDate(availableFrom),
      'locality': locality,
      'localityIsCustom': localityIsCustom,
      'fullAddress': fullAddress,
      'lat': lat,
      'lng': lng,
      'amenities': amenities,
      'photos': photos,
      'coverPhoto': coverPhoto,
      'status': status.value,
      'rejectionReason': rejectionReason,
      'reviewedBy': reviewedBy,
      'reviewedByName': reviewedByName,
      'reviewedByRole': reviewedByRole,
      'reviewedAt': reviewedAt != null ? Timestamp.fromDate(reviewedAt!) : null,
      'createdAt': Timestamp.fromDate(createdAt),
      'updatedAt': Timestamp.fromDate(updatedAt),
      'distanceFromOfficeKm': distanceFromOfficeKm,
      'isArchived': isArchived,
    };
  }

  factory ListingModel.fromDocument(DocumentSnapshot doc) {
    final data = doc.data() as Map<String, dynamic>? ?? {};
    return ListingModel.fromMap(data, doc.id);
  }

  factory ListingModel.fromMap(Map<String, dynamic> map, String docId) {
    DateTime parseDateTime(dynamic val) {
      if (val is Timestamp) return val.toDate();
      if (val is String) return DateTime.tryParse(val) ?? DateTime.now();
      if (val is int) return DateTime.fromMillisecondsSinceEpoch(val);
      return DateTime.now();
    }

    final rawPhotos = (map['photos'] as List<dynamic>?)?.map((e) => e.toString()).toList() ?? [];
    final cover = map['coverPhoto']?.toString() ?? (rawPhotos.isNotEmpty ? rawPhotos.first : '');

    return ListingModel(
      id: docId,
      ownerId: map['ownerId'] ?? '',
      ownerName: map['ownerName'] ?? 'Owner',
      ownerPhone: map['ownerPhone'] ?? '',
      whatsappNumber: map['whatsappNumber'],
      title: map['title'] ?? '',
      description: map['description'] ?? '',
      type: PropertyType.fromString(map['type']),
      rentPerMonth: (map['rentPerMonth'] as num?)?.toDouble() ?? 0.0,
      securityDeposit: (map['securityDeposit'] as num?)?.toDouble() ?? 0.0,
      furnishing: FurnishingType.fromString(map['furnishing']),
      bedrooms: (map['bedrooms'] as num?)?.toInt() ?? 1,
      bathrooms: (map['bathrooms'] as num?)?.toInt() ?? 1,
      genderPreference: GenderPreference.fromString(map['genderPreference']),
      availableFrom: parseDateTime(map['availableFrom']),
      locality: map['locality'] ?? '',
      localityIsCustom: map['localityIsCustom'] == true,
      fullAddress: map['fullAddress'] ?? '',
      lat: (map['lat'] as num?)?.toDouble(),
      lng: (map['lng'] as num?)?.toDouble(),
      amenities: (map['amenities'] as List<dynamic>?)?.map((e) => e.toString()).toList() ?? [],
      photos: rawPhotos,
      coverPhoto: cover,
      status: ListingStatus.fromString(map['status']),
      rejectionReason: map['rejectionReason'],
      reviewedBy: map['reviewedBy'],
      reviewedByName: map['reviewedByName'],
      reviewedByRole: map['reviewedByRole'],
      reviewedAt: map['reviewedAt'] != null ? parseDateTime(map['reviewedAt']) : null,
      createdAt: parseDateTime(map['createdAt']),
      updatedAt: parseDateTime(map['updatedAt']),
      distanceFromOfficeKm: (map['distanceFromOfficeKm'] as num?)?.toDouble(),
      isArchived: map['isArchived'] == true,
    );
  }

  ListingModel copyWith({
    String? id,
    String? ownerId,
    String? ownerName,
    String? ownerPhone,
    String? whatsappNumber,
    String? title,
    String? description,
    PropertyType? type,
    double? rentPerMonth,
    double? securityDeposit,
    FurnishingType? furnishing,
    int? bedrooms,
    int? bathrooms,
    GenderPreference? genderPreference,
    DateTime? availableFrom,
    String? locality,
    bool? localityIsCustom,
    String? fullAddress,
    double? lat,
    double? lng,
    List<String>? amenities,
    List<String>? photos,
    String? coverPhoto,
    ListingStatus? status,
    String? rejectionReason,
    bool clearRejectionReason = false,
    String? reviewedBy,
    String? reviewedByName,
    String? reviewedByRole,
    DateTime? reviewedAt,
    DateTime? createdAt,
    DateTime? updatedAt,
    double? distanceFromOfficeKm,
    bool? isArchived,
  }) {
    return ListingModel(
      id: id ?? this.id,
      ownerId: ownerId ?? this.ownerId,
      ownerName: ownerName ?? this.ownerName,
      ownerPhone: ownerPhone ?? this.ownerPhone,
      whatsappNumber: whatsappNumber ?? this.whatsappNumber,
      title: title ?? this.title,
      description: description ?? this.description,
      type: type ?? this.type,
      rentPerMonth: rentPerMonth ?? this.rentPerMonth,
      securityDeposit: securityDeposit ?? this.securityDeposit,
      furnishing: furnishing ?? this.furnishing,
      bedrooms: bedrooms ?? this.bedrooms,
      bathrooms: bathrooms ?? this.bathrooms,
      genderPreference: genderPreference ?? this.genderPreference,
      availableFrom: availableFrom ?? this.availableFrom,
      locality: locality ?? this.locality,
      localityIsCustom: localityIsCustom ?? this.localityIsCustom,
      fullAddress: fullAddress ?? this.fullAddress,
      lat: lat ?? this.lat,
      lng: lng ?? this.lng,
      amenities: amenities ?? this.amenities,
      photos: photos ?? this.photos,
      coverPhoto: coverPhoto ?? this.coverPhoto,
      status: status ?? this.status,
      rejectionReason: clearRejectionReason ? null : (rejectionReason ?? this.rejectionReason),
      reviewedBy: reviewedBy ?? this.reviewedBy,
      reviewedByName: reviewedByName ?? this.reviewedByName,
      reviewedByRole: reviewedByRole ?? this.reviewedByRole,
      reviewedAt: reviewedAt ?? this.reviewedAt,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      distanceFromOfficeKm: distanceFromOfficeKm ?? this.distanceFromOfficeKm,
      isArchived: isArchived ?? this.isArchived,
    );
  }
}
