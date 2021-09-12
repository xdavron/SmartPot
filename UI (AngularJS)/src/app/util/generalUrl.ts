export class GeneralURL {
    private static RESOURCE_URL = 'https://smart-pot-catalog.herokuapp.com/';
    private static MANUAL_URL = 'https://smart-pot-manual-mode.herokuapp.com/';
    private static AUTOMATIC_URL = 'https://smart-pot-auto-mode.herokuapp.com/';
    private static MODE_URL = 'https://smart-pot-mode-manager.herokuapp.com/';
    public static FEED_URL = 'https://smart-pot-feedback-mode.herokuapp.com/';


    public static resourceURL: string = GeneralURL.RESOURCE_URL + 'broker/';
    public static topicsURL: string = GeneralURL.RESOURCE_URL + 'topics/';
    public static addURL: string = GeneralURL.RESOURCE_URL + 'add';
    public static removeURL: string = GeneralURL.RESOURCE_URL + 'remove';
    public static urlsURL: string = GeneralURL.RESOURCE_URL + 'urls/';



    public static manualURL: string = GeneralURL.MANUAL_URL;
    public static modeURL: string = GeneralURL.MODE_URL;


}
