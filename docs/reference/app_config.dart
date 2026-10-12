/// Central application configuration.
/// Any app-wide name, company details, or default presets are declared here
/// so they can easily be customized or rebranded in a single location.
class AppConfig {
  AppConfig._();

  // App Identity
  static const String appName = 'NestFinder';
  static const String appTagline = 'Verified Accommodation for Atomic North';
  static const String companyName = 'Atomic North Pvt Ltd';
  static const String companyLocation = 'Billawar, Jammu & Kashmir';
  static const String supportEmail = 'khanbasharat@gmail.com';
  static const String appVersion = 'Version 1.0.0';

  // Photo Storage Provider ('cloudinary' or 'firebase')
  static const String imageProvider = 'cloudinary';
  static const String cloudinaryCloudName = 'khan-developers';
  static const String cloudinaryUploadPreset = 'accommodation_unsigned';
  static const String cloudinaryFolder = 'listings';

  // Office Location Defaults (Billawar Headquarters)
  static const String officeName = 'Atomic North Campus, Billawar';
  static const double officeLatitude = 32.6105;
  static const double officeLongitude = 75.6027;
  static const String officeAddress = 'Atomic North Campus, Billawar, Kathua, J&K - 184204';

  // Initial Configuration Presets (Synced or overridden by Firestore config/app)
  static const List<String> defaultPropertyTypes = [
    'flat',
    'house',
    'room',
    'pg',
    'hostel',
  ];

  static const List<String> defaultFurnishingOptions = [
    'furnished',
    'semi',
    'unfurnished',
  ];

  static const List<String> defaultGenderPreferences = [
    'any',
    'male',
    'female',
  ];

  static const List<String> defaultLocalities = [
    'Billawar Main Bazar',
    'Mandli',
    'Dingi Simbli',
    'Phinter',
    'Kishanpur',
    'Dewal',
    'Durang',
  ];

  static const List<String> defaultAmenities = [
    'WiFi',
    '24x7 Water Supply',
    'Power Backup',
    'Geyser / Hot Water',
    'Attached Bathroom',
    'Kitchen Access',
    'Parking (Bike)',
    'Parking (Car)',
    'RO Drinking Water',
    'Laundry / Washing Machine',
    'CCTV / Secure',
    'Meals Available',
  ];

  // Pagination & Upload Limits
  static const int listingPageSize = 15;
  static const int minPhotosRequired = 2;
  static const int maxPhotosAllowed = 8;
  static const int maxImageUploadBytes = 1024 * 1024; // 1 MB
  static const int imageTargetWidth = 1280;
  static const int imageCompressQuality = 80;
}
