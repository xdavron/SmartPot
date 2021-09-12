import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, NavigationEnd, Router } from '@angular/router';
import { ResourceService } from '../services/resource.service';

@Component({
  selector: 'app-rose',
  templateUrl: './rose.component.html',
  styleUrls: ['./rose.component.scss']
})
export class RoseComponent implements OnInit {
  public plants: any[];

  public plant: any;
  public plantId: string = '';
  public plantName: string = '';
  public isManual: boolean = false;
  public isAuto: boolean = false;
  public isFeed: boolean = false;

  constructor(private activeRoute: ActivatedRoute, private router: Router, private  resourceService: ResourceService) {
    this.plants = [];
  }

  ngOnInit(): void {

    if (window.innerWidth < 1200) {
      (<HTMLElement>document.getElementById("bekorJoy")).style.display = "none";
    }
    this.activeRoute.paramMap.subscribe(paramMap => {

      this.plantId = paramMap.get('flower') || '';
      this.getPlant()
      this.getPlantStatus()

    })

    this.activeRoute.queryParams.subscribe(queryParams => {
      if (queryParams['manual'] === 'true') {
        this.isManual = true;
        document.getElementById('manuId')?.classList.add('active')
      }
      if (queryParams['auto'] === 'true') {
        this.isAuto = true;
        document.getElementById('autoId')?.classList.add('active')
      }
      if (queryParams['feedback'] === 'true') {
        this.isFeed = true;
        document.getElementById('feedbackId')?.classList.add('active')
      }
    })
  }

  private getPlant() {
    this.plants = [];

    this.resourceService.getTopics().subscribe(
      (data) => {
        for (const x in data) {
          data[x]['id'] = x;
          if (x == 'plant1' || x == 'plant2' || x == 'plant3' || x == 'plant4' || x == 'plant5') {
            data[x]['imageUrl'] = '../../assets/images/' + x + '.jpeg';
          } else {
            data[x]['imageUrl'] = '../../assets/images/default.jpeg';
          }
          this.plants.push(data[x])
          if (x === this.plantId) {
            this.plant = data[x]
            this.plantName = data[x]['name'];
          }
        }
      },
      error => {
        console.log(error);
      }
    );
  }

  private getPlantStatus() {
    this.resourceService.getPlantStatus(this.plantId).subscribe(
      (data) => {
        if (data.includes('manual')) {
          this.isManual = true;
          document.getElementById('manuId')?.classList.add('active')
        }
        if (data.includes('auto')) {
          this.isAuto = true;
          document.getElementById('autoId')?.classList.add('active')
        }
        if (data.includes('feedback')) {
          this.isFeed = true;
          document.getElementById('feedbackId')?.classList.add('active')
        }

        if (this.plantId === "plant1") {
          this.router.navigate(['./'],
            {
              relativeTo: this.activeRoute,
              queryParams: { manual: this.isManual, auto: this.isAuto, feedback: this.isFeed },
              queryParamsHandling: 'merge'
            }
          )
        } else {
          this.router.navigate(['./manual'],
            {
              relativeTo: this.activeRoute,
              queryParams: { manual: this.isManual, auto: this.isAuto, feedback: this.isFeed },
              queryParamsHandling: 'merge'
            }
          )
        }
      },
      error => {
        console.log(error);
      }
    );
  }

  public deletePlant() {
    let plant = {
      "id": this.plantId
    }

    this.resourceService.removePlant(JSON.stringify(plant)).subscribe(
      (data) => {
        document.getElementById("closeDelete")?.click();
        this.router.navigate(['']);
      },
      (error) => {
        console.log(error);
      }
    )
  }

  private getManual() {
    return this.activeRoute.snapshot.queryParamMap.get('manual')==='true';
  }

  private getAuto() {
    return this.activeRoute.snapshot.queryParamMap.get('auto')==='true';
  }

  private getFeed() {
    return this.activeRoute.snapshot.queryParamMap.get('feedback')==='true';
  }

  goToLink(link: string) {
    this.router.navigate([link],
      {
        relativeTo: this.activeRoute,
        queryParams: { manual: this.getManual(), auto: this.getAuto(), feedback: this.getFeed() },
        queryParamsHandling: 'merge'
      }
    )
  }

}
