import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { GeneralURL } from '../util/generalUrl';
import { PlantDTO } from '../util/plantDto';

@Injectable({
  providedIn: 'root'
})
export class ResourceService {

  constructor(private http: HttpClient) { }

  public getTopics() {
    return this.http.get<Array<any>>(GeneralURL.topicsURL);
  }

  public startSystem() {
    return this.http.post(GeneralURL.modeURL + 'system/start', '');
  }

  public addPlant(plant: string) {
    return this.http.post(GeneralURL.addURL, plant);
  }

  public removePlant(plant: string) {
    return this.http.post(GeneralURL.removeURL, plant);
  }

  public getPlantStatus (id: string): Observable<Array<string>> {
    return this.http.get<Array<string>>(GeneralURL.modeURL + id + "/status");
  }

  public setPlantStatus(id: String, status: String) {
    return this.http.post(GeneralURL.modeURL + id + "/manual/" + status, '');
  }

  public setPlantStatusAutoEnableWithData(id: string, plant: string) {
    return this.http.post(GeneralURL.modeURL + id + "/auto/enable/?newSchedule=True", plant);
  }

  public setPlantAutoSchedule(id: string, plant: string) {
    return this.http.post(GeneralURL.modeURL + id + "/auto/newSchedule", plant);
  }

  public setPlantStatusAutoEnable(id: String) {
    return this.http.post(GeneralURL.modeURL + id + "/auto/enable/?newSchedule=False", '');
  }

  public setPlantStatusAutoDisable(id: String) {
    return this.http.post(GeneralURL.modeURL + id + "/auto/disable", '');
  }

  public setPlantStatusFeedbackEnable(id: String, body: string) {
    return this.http.post(GeneralURL.modeURL + id + "/feedback/enable", body);
  }

  public setFeedbackParams(id: String, body: string) {
    return this.http.post(GeneralURL.modeURL + id + "/feedback/paramChange", body);
  }

  public getFeedbackParams(id: String) {
    return this.http.get(GeneralURL.FEED_URL + id + "/thresholds");
  }

  public setPlantStatusFeedbackDisable(id: String) {
    return this.http.post(GeneralURL.modeURL + id + "/feedback/disable", '');
  }

  public setPlantWater(plant: any) {

    let json = JSON.stringify(plant);

    return this.http.post(GeneralURL.manualURL + plant['plantId'] + "/waterControl", json);

  }

  public stopPlantWater(plant: any) {

    let json = JSON.stringify(plant);

    return this.http.post(GeneralURL.manualURL + plant['plantId'] + "/waterControl", json);

  }

  public startPlantLight(plant: any) {

    let json = JSON.stringify(plant);

    return this.http.post(GeneralURL.manualURL + plant['plantId'] + "/lightControl", json);

  }

  public stopPlantLight(plant: any) {

    let json = JSON.stringify(plant);

    return this.http.post(GeneralURL.manualURL + plant['plantId'] + "/lightControl", json);

  }

  public getAutomaticSchedule(id: string) {
    return this.http.get<Array<any>>(GeneralURL.modeURL + id + "/auto/schedule/weekly");
  }

}
