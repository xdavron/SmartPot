import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { ResourceService } from 'src/app/services/resource.service';
import { PlantDTO } from 'src/app/util/plantDto';

@Component({
  selector: 'app-manual',
  templateUrl: './manual.component.html',
  styleUrls: ['./manual.component.scss']
})
export class ManualComponent implements OnInit {

  public activeStatus;
  private plantId = "";
  private isFeed: boolean = false;
  public waterStat: boolean = false;
  public lightStat: boolean = false;

  constructor(private router: Router, private  resourceService: ResourceService, private activeRoute: ActivatedRoute) {
    this.activeStatus = false;
  }

  ngOnInit(): void {
    this.activeRoute.queryParamMap.subscribe(paramMap => {
      this.activeStatus = paramMap.get("manual")==="true";
    })

    this.plantId = this.router.url.split('/')[1].split('?')[0];

    this.getPlantStatus();
  }

  public changeStatus() {
    if (this.activeStatus) {
      this.resourceService.setPlantStatus(this.plantId, 'disable').subscribe(
        (data) => {
          this.activeStatus = false
          document.getElementById('manuId')?.classList.remove('active')

          this.router.navigate(['.'],
            {
              relativeTo: this.activeRoute,
              queryParams: { manual: false },
              queryParamsHandling: 'merge'
            })
        },
        error => {
          console.log(error);
        }
      )
    } else {
      if (!this.isFeed) {
        this.resourceService.setPlantStatus(this.plantId, 'enable').subscribe(
          (data) => {

            this.activeStatus = true
            document.getElementById('manuId')?.classList.add('active')

            this.router.navigate(['.'],
              {
                relativeTo: this.activeRoute,
                queryParams: { manual: true },
                queryParamsHandling: 'merge'
              })
          },
          error => {
            console.log(error);
          }
        )
      } else {
        document.getElementById("errButton")?.click();
        (<HTMLInputElement>document.getElementById("customSwitch1")).checked = false;
      }
    }
  }

  private getPlantStatus() {
    this.resourceService.getPlantStatus(this.plantId).subscribe(
      (data) => {
        if (data.includes('feedback')) {
          this.isFeed = true;
        }
      },
      error => {
        console.log(error);
      }
    );
  }

  public startWatering() {
    let duration = parseInt((<HTMLInputElement>document.getElementById("waterDuration")).value);
    if (duration.toString() == "NaN") {
      duration = -1;
    } else {
      setTimeout(() => {
        this.stopWatering()
      }, duration * 1000);
    }
    this.waterStat = true;


    let plant = {
      'plantId': this.plantId,
      'action': 'on',
      'duration': duration
    };

    console.log(plant);

    this.resourceService.setPlantWater(plant).subscribe(
      (data) => {
        console.log(data);
      },
      error => {
        console.log(error);
      }
    )
  }

  public stopWatering() {
    this.waterStat = false;

    let plant = {
      'plantId': this.plantId,
      'action': 'off',
      'duration': 0
    };
    (<HTMLInputElement>document.getElementById("waterDuration")).value = "";

    console.log(plant);

    this.resourceService.stopPlantWater(plant).subscribe(
      (data) => {
        console.log(data);
      },
      error => {
        console.log(error);
      }
    )
  }

  public startLightning () {
    let duration = parseInt((<HTMLInputElement>document.getElementById("lightDuration")).value);
    if (duration.toString() == "NaN") {
      duration = -1;
    } else {
      setTimeout(() => {
        this.stopLightning()
      }, duration * 1000);
    }
    this.lightStat = true;

    let plant = {
      'plantId': this.plantId,
      'action': 'on',
      'duration': duration
    };

    console.log(plant);

    this.resourceService.startPlantLight(plant).subscribe(
      (data) => {
        console.log(data);
      },
      error => {
        console.log(error);
      }
    )

  }

  public stopLightning () {
    this.lightStat = false;

    let plant = {
      'plantId': this.plantId,
      'action': 'off',
      'duration': 0
    };

    (<HTMLInputElement>document.getElementById("lightDuration")).value = "";

    console.log(plant);

    this.resourceService.stopPlantLight(plant).subscribe(
      (data) => {
        console.log(data);
      },
      error => {
        console.log(error);
      }
    )
  }
}
