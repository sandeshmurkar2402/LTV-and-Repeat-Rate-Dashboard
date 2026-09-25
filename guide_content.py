"""Static content for the dashboard's User Guide tab (edit here; not linked to any sheet)."""

GUIDE_SECTIONS = [{'title': 'LTV',
  'intro': 'This tab shows the total number of users acquired and the total revenue contributed by those '
           'users, broken down by acquisition month. The data is further split by business line.',
  'options': []},
 {'title': 'Repeat Rate',
  'intro': 'These tabs are designed to track the month-on-month repeat behavior of cohorts based on the '
           'month in which users were acquired.\n'
           'The following views are available under the Repeat Rate section:',
  'options': [('Overall',
               'This view shows the overall monthly repeat-rate cohorts. You can view the metrics in '
               'absolute values or as a repeat-rate percentage, and select the required month range.\n'
               '\n'
               'Below the main Repeat Rate % table, you will also find:\n'
               'An option to download the current view using the CSV button.\n'
               'A Repeat Rate % - Period-over-Period Change table, which shows the month-on-month change in '
               'the metrics.\n'
               'An option to select the display mode as Absolute or %.'),
              ('By Business Line',
               'This view provides the overall repeat rate split across business lines.\n'
               'You can use the Expand All and Collapse All options to view or hide all business-line '
               'cohorts. Alternatively, you can expand or collapse individual months by clicking the + / − '
               'options next to the month names.\n'
               'This expand/collapse functionality is available across all views where multiple levels of '
               'breakdown are available.\n'
               'You can also filter specific business lines using the Business Line filter. The default '
               'value is All.\n'
               'The option to download the data as a CSV and the Repeat Rate % - Period-over-Period Change '
               'table are also available, as explained in the Overall view.'),
              ('By Platform',
               'This view provides the same functionality as the other Repeat Rate views, but the cohorts '
               'are split by platform - iOS, Android, and Web.\n'
               'You can also select a specific platform using the Platform filter available in the second '
               'dropdown.'),
              ('By FO Value Bucket',
               'This view is similar to the By Business Line and By Platform views described above.\n'
               'It tracks repeat-rate cohorts based on the First Order (FO) Value Bucket of newly acquired '
               'users.'),
              ('Cross Sales',
               'This tab is designed to track whether users acquired through one business line go on to make '
               'repeat purchases from other business lines.\n'
               'There are two filters available:\n'
               'Acquisition Business Line - the business line through which the user was originally '
               'acquired.\n'
               'CM Business Line - the business line in the current month. CM stands for Current Month.\n'
               'Multiple business lines can be selected in both filters'),
              ('Cross Sales - Platform x BL',
               'This view is an extension of the Cross Sales view described above.\n'
               'In addition to tracking cross-business-line purchases, it shows the platform that users '
               'prefer to use for their subsequent orders for a particular business line.')]},
 {'title': 'Recency',
  'intro': 'This tab is designed to track how far in advance users register for a session relative to the '
           'actual session date.\n'
           'You can select between Group Online and Group Offline business lines.\n'
           'You can also select the required metric:\n'
           'Revenue, Purchases, Users\n'
           'The metrics can be viewed either as Absolute values or as % of Total.',
  'options': []},
 {'title': 'Purchase Month & Session Month',
  'intro': 'Both tabs have identical views and functionalities. The key difference is the date used for '
           'reporting:\n'
           'Session Month - data is grouped based on the session date.\n'
           'Purchase Month - data is grouped based on the actual registration/purchase date of the user.\n'
           'The following views are available under both tabs.',
  'options': [('Overall',
               'This view shows the month-on-month performance for: Total & New Repeat  - Revenue, '
               'Purchases, Users & AOV along with overall ARPU'),
              ('Business Line',
               'This view provides a business-line-wise breakdown of: Total & New Repeat  - Revenue, '
               'Purchases, Users & AOV along with overall ARPU. You can use the filter to select a specific '
               'business line.'),
              ('Platform',
               'This view provides a platform wise breakdown of: Total & New Repeat  - Revenue, Purchases, '
               'Users & AOV along with overall ARPU. You can use the filter to select a specific platform.'),
              ('Business Line & Platform',
               'This view shows New and Repeat metrics by business line, along with the corresponding '
               'platform-wise breakdown.\n'
               'The view can become relatively detailed when all business lines and platforms are expanded. '
               'Therefore, it is recommended to select a specific business line or platform when a more '
               'focused view is required.'),
              ('BL Contribution to Platform',
               'This view shows the contribution of each business line to key metrics such as Revenue, '
               'Users, and Purchases.\n'
               'When All options are selected, you can see the business-line contribution to the overall '
               'metrics. You can also view the contribution separately for New and Repeat users.\n'
               'When a specific platform is selected, the view shows the contribution of each business line '
               "to that platform's Revenue, Purchases, Users, etc. The New/Repeat breakdown is also "
               'available.\n'
               'Example: During Aug-26, 1on1 contributed 56% of the total iOS App revenue.'),
              ('Platform Contribution to BL',
               'This view shows the contribution of different platforms to each business line.\n'
               'When no specific business line is selected, the view shows the share of revenue coming from '
               'Android, iOS, Web, and Untagged platforms.\n'
               'When a specific business line is selected, the view shows the platform-wise contribution to '
               "that business line's revenue.\n"
               'Example: During Aug-26, for 1on1: Android contributed 25.7% of 1on1 revenue. iOS contributed '
               '35% of 1on1 revenue. Web contributed 37% of 1on1 revenue. 2.7% of 1on1 revenue did not have '
               'a platform tag.\n'
               'You can further analyze the platform contribution across different metrics, including '
               'Purchases, Users, AOV, and New/Repeat.')]}]
